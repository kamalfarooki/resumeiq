import os
import uuid
import time
import json

from flask import (
    Flask, render_template, request, redirect,
    url_for, session, jsonify, send_file, flash
)
from werkzeug.utils import secure_filename

from services.parser import extract_text
from services.ats_engine import analyze_resume
from services.pdf_generator import create_pdf

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
REPORT_FOLDER = os.path.join(BASE_DIR, "reports")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(REPORT_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024  # 8 MB upload limit

ALLOWED_EXTENSIONS = {"pdf", "docx", "txt"}

# --------------------------------------------------------------------
# Per-visitor server-side storage.
#
# Flask's default session cookie is signed but stored client-side, which
# caps it at ~4KB - far too small for a resume's full text + analysis.
# Instead we keep a short random id in the cookie and store the actual
# data server-side, keyed by that id.
#
# If REDIS_URL is set, records are stored in Redis with a TTL — this is
# what makes it safe to run more than one worker/instance, since every
# worker reads and writes the same store instead of its own private
# memory. If REDIS_URL isn't set (e.g. local development), it falls back
# to a plain in-memory dict, which only works correctly with exactly one
# worker process.
# --------------------------------------------------------------------
STORE_TTL_SECONDS = 60 * 60 * 6  # 6 hours

REDIS_URL = os.environ.get("REDIS_URL")
_redis = None

if REDIS_URL:
    import redis
    _redis = redis.from_url(REDIS_URL, decode_responses=True)

# In-memory fallback store, only actually used when REDIS_URL isn't set.
_MEMORY_STORE = {}


def _redis_key(sid):
    return f"resumeiq:session:{sid}"


def _cleanup_store():
    # Redis expires keys on its own via SETEX below; only the in-memory
    # fallback needs manual sweeping.
    if _redis:
        return
    now = time.time()
    expired = [k for k, v in _MEMORY_STORE.items() if now - v.get("_ts", now) > STORE_TTL_SECONDS]
    for k in expired:
        _MEMORY_STORE.pop(k, None)


def get_session_id():
    if "sid" not in session:
        session["sid"] = uuid.uuid4().hex
    return session["sid"]


def get_record():
    sid = session.get("sid")
    if not sid:
        return None

    if _redis:
        raw = _redis.get(_redis_key(sid))
        return json.loads(raw) if raw else None

    return _MEMORY_STORE.get(sid)


def save_record(resume_text, jd_text, result, filename=None):
    sid = get_session_id()
    existing = get_record() or {}

    record = {
        "resume_text": resume_text,
        "jd_text": jd_text,
        "result": result,
        "filename": filename or existing.get("filename"),
    }

    if _redis:
        _redis.setex(_redis_key(sid), STORE_TTL_SECONDS, json.dumps(record))
    else:
        record["_ts"] = time.time()
        _MEMORY_STORE[sid] = record


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ============================================================
# ROUTES
# ============================================================

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    _cleanup_store()

    file = request.files.get("resume")
    jd_text = (request.form.get("job_description") or "").strip()

    if not file or file.filename == "":
        flash("Please choose a resume file to upload.", "error")
        return redirect(url_for("home"))

    if not allowed_file(file.filename):
        flash("Unsupported file type. Please upload a PDF, DOCX or TXT file.", "error")
        return redirect(url_for("home"))

    safe_name = secure_filename(file.filename)
    unique_name = f"{uuid.uuid4().hex}_{safe_name}"
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], unique_name)
    file.save(filepath)

    try:
        text = extract_text(filepath)
    except Exception:
        flash("We couldn't read that file. Please try a different PDF or DOCX.", "error")
        return redirect(url_for("home"))
    finally:
        # We don't need to keep the uploaded file around once text is extracted.
        try:
            os.remove(filepath)
        except OSError:
            pass

    if not text or not text.strip():
        flash("No readable text was found in that file. Scanned/image-only PDFs aren't supported yet.", "error")
        return redirect(url_for("home"))

    result = analyze_resume(text, jd_text)
    save_record(text, jd_text, result, filename=safe_name)

    return redirect(url_for("result"))


@app.route("/result")
def result():
    record = get_record()
    if not record:
        flash("Please analyze a resume first.", "error")
        return redirect(url_for("home"))

    return render_template(
        "result.html",
        data=record["result"],
        resume_text=record["resume_text"],
        jd_text=record["jd_text"],
        filename=record.get("filename"),
    )


@app.route("/rescore", methods=["POST"])
def rescore():
    """
    Live re-scoring endpoint used by the in-browser resume editor.
    Accepts edited resume text (and optional JD text) as JSON and
    returns the freshly computed analysis as JSON.
    """
    record = get_record()
    if not record:
        return jsonify({"error": "No active session. Please upload a resume first."}), 400

    payload = request.get_json(silent=True) or {}
    resume_text = payload.get("resume_text", "")
    jd_text = payload.get("jd_text", record.get("jd_text", ""))

    if not resume_text or not resume_text.strip():
        return jsonify({"error": "Resume text can't be empty."}), 400

    if len(resume_text) > 20000:
        return jsonify({"error": "Resume text is too long."}), 400

    result = analyze_resume(resume_text, jd_text)
    save_record(resume_text, jd_text, result, filename=record.get("filename"))

    return jsonify({"ok": True, "data": result})


@app.route("/download")
def download():
    record = get_record()
    if not record:
        flash("Please analyze a resume first.", "error")
        return redirect(url_for("home"))

    sid = session.get("sid", "report")
    filename = f"ResumeIQ_Report_{sid[:8]}.pdf"
    filepath = os.path.join(REPORT_FOLDER, filename)

    create_pdf(record["result"], filepath)

    return send_file(
        filepath,
        as_attachment=True,
        download_name="ResumeIQ_Report.pdf"
    )


@app.route("/healthz")
def healthz():
    return jsonify({"status": "ok"})


LEGAL_LAST_UPDATED = "July 2026"


@app.route("/privacy")
def privacy():
    return render_template("privacy.html", updated_date=LEGAL_LAST_UPDATED)


@app.route("/terms")
def terms():
    return render_template("terms.html", updated_date=LEGAL_LAST_UPDATED)


@app.route("/about")
def about():
    return render_template("about.html")


@app.errorhandler(413)
def too_large(_e):
    flash("That file is too large. Please upload something under 8MB.", "error")
    return redirect(url_for("home"))


@app.errorhandler(404)
def not_found(_e):
    return render_template("404.html"), 404


@app.errorhandler(500)
def server_error(_e):
    return render_template("500.html"), 500


if __name__ == "__main__":
    debug_mode = os.environ.get("FLASK_DEBUG", "1") == "1"
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=debug_mode, port=port)
