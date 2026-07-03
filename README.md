# ResumeIQ

Upload a resume, get an ATS score with a full breakdown, paste a job description
to see what's missing, then edit the resume text right in the browser and
re-score it instantly — no re-upload required.

---

## What changed in this pass

**Fixed (the app was actually broken):**
- `services/ats_engine.py` had a syntax error — a dictionary literal was closed
  with `}` and then more keys were appended after it. The app could not start
  in its previous state. Screenshots from before this fix were running on an
  older cached version.
- `services/pdf_generator.py` crashed on download — it tried to concatenate a
  string with a recommendation *dict*. Fixed to render title/priority/message.
- The "Paste Job Description" box on the upload page was captured by the form
  but never read by the backend. It's now wired end-to-end into scoring.
- `.txt` was accepted by the file picker but not handled by the text
  extractor. Added.
- The results template referenced fields that don't exist anywhere in the
  data (`resume_strength`, `overall_feedback`, etc.) and looped over
  `top_roles` with the wrong shape — both would have thrown Jinja errors.
  Rebuilt the template against the real data shape.
- The app stored the last analysis in a single global Python variable, so two
  people using the site at the same time would see each other's resumes.
  Replaced with a per-visitor server-side store keyed off a session cookie.
- Removed dead/unused files that weren't wired into anything:
  `resume_parser.py`, `analyzer.py`, `role_detector.py`, `pdf_report.py`,
  empty `config.py` / `utils/helpers.py`, and duplicate/unused entries in
  `requirements.txt`.

**New — the feature you asked for:**
- **Live resume editor.** The results page is a two-pane workbench: your
  resume text on the left (editable), your live ATS score on the right.
  Hit "Re-score edits" (or `Cmd/Ctrl+Enter`) and the score, grade, skill
  gaps, section checklist, and JD match all update in place via `/rescore`
  — no page reload.
- **Real JD matching.** `services/jd_matcher.py` now compares the skills the
  job description actually asks for against your resume's skills (not just
  raw word overlap), and shows matched vs. missing skills with a match %.
- **Smarter recommendations.** Split into targeted gaps (based on what's
  actually missing from *this* resume) vs. general tips, sorted by priority,
  and now includes a JD-specific "skills the JD wants but your resume
  doesn't mention" callout when a JD is pasted.
- Full UI redesign — the previous templates had duplicated inline scripts,
  broken emoji encoding, and mismatched data bindings. See "Design" below.

---

## v3 — Multi-domain support (Finance & Accounting added)

A real bug surfaced by testing with a non-IT resume: the entire skill/role
database only ever covered IT/DevOps. Any Finance, Sales, or other
non-technical resume scored against IT criteria, found nothing, and
silently defaulted to whatever role happened to be listed first in
`roles.json` ("Site Reliability Engineer") — regardless of what the resume
actually said.

**Fixed:**
- `data/skills.json` and `data/roles.json` are now domain-tagged
  (`Information Technology`, `Finance & Accounting`). `services/skill_matcher.py`
  detects which domain a resume belongs to based on which domain's skills
  actually appear in it, and scopes role matching, missing-skill gaps, and
  certification suggestions to that domain.
- `services/role_matcher.py`'s `best_role()` now returns `None` when there's
  truly no meaningful skill overlap, instead of returning an arbitrary
  0%-coverage role. `ats_engine.py` falls back to a title-keyword guess (or
  a generic "Professional" label) rather than asserting a specific wrong role.
- Section detection (`analyze_sections`) was rewritten to look for actual
  section *headers* in the resume (with typo-tolerant fuzzy matching, so
  "EXPERICENCE" or "ACHEIVEMENT" still count) instead of searching the whole
  document for a keyword substring. The old approach missed "LANGUAGE
  SKILLS" (no literal "languages") and had no way to recognize a
  certifications section that listed non-IT credentials.
- `services/parser.py`'s certification extraction previously matched bare
  platform names like "AWS" as a "certification" just because the word
  appeared anywhere — which meant a resume that merely *mentioned* AWS as a
  skill was credited with holding an AWS certification. Fixed to require
  certification-specific phrasing ("AWS Certified", "AWS Solutions
  Architect"), and extended to recognize Finance certifications (ACCA, CPA,
  CFA, CMA, CIA, ICWAI, FRM, ...).
- `skill_score` in `scoring_engine.py` used to score by raw skill count,
  which unfairly penalized domains with a smaller reference skill list
  (Finance has ~47 tracked skills vs. IT's ~150). It now scores by coverage
  percentage of the detected domain's own skill pool.

**Adding another domain (Sales, Healthcare, etc.) later:** add a new
top-level key to `data/skills.json` with its categories/skills, add
matching role entries to `data/roles.json` with `"domain": "Your Domain"`,
and optionally add title keywords to `TITLE_KEYWORDS_BY_DOMAIN` in
`services/ats_engine.py`. Nothing else needs to change — domain detection,
role matching, and coverage scoring all read from those two files.

---

## v4 — All-sector coverage, trending skills, recruiter tips

**Expanded domain coverage from 2 to 10 sectors:** Information Technology,
Finance & Accounting, Sales & Marketing, Human Resources, Healthcare &
Nursing, Design & Creative, Legal, Operations & Supply Chain, Customer
Support & Success, and Education & Training — each with its own skill
taxonomy and role definitions in `data/skills.json` / `data/roles.json`.
Domain detection, role matching, and coverage scoring are fully
data-driven, so adding an 11th sector is a data-file change, not a code
change (see the note further down).

**New — "what to add to get a callback":**
- **Trending skills tab.** Each role in `roles.json` now has a
  `trending_skills` list (e.g. Generative AI/LLM tooling for ML roles, ESG
  Reporting for Finance, Programmatic Advertising for Marketing). The
  workbench surfaces whichever of these aren't already on the resume —
  this is the "latest technologies for your field" recommendation.
- **Recruiter tips tab.** A new, separate category from ATS-structure
  recommendations, focused specifically on getting *found and shortlisted*:
  missing LinkedIn URL, lack of quantified achievements (detected via a
  numbers/percent/dollar-figure scan of the actual text), exact job-title
  matching, and literal JD-keyword matching advice. Mixes universal,
  evergreen guidance with a couple of checks that react to the specific
  resume.
- `services/parser.py` now also extracts a LinkedIn URL/handle (including
  the common case where a resume shows only the LinkedIn *icon* next to a
  bare "@handle", with no literal word "linkedin" in the extracted text).

**Performance:** skill-matching regex patterns (now ~400 skills across 10
domains) are precompiled once at process start instead of being rebuilt on
every request. Measured end-to-end — file upload through parsing, domain
detection, scoring, and rendering — at roughly 60ms per resume, most of
which is Flask/template overhead rather than the analysis itself. Re-scoring
edited text in the live editor is faster still since there's no file I/O.

---

## v5 — Learning resources tab, Wording & mistakes tab

**Learning tab:** for every missing core skill, trending skill, and
recommended certification, the workbench now shows *where to actually go
learn it* — official certifying-body pages for certifications
(`data/learning_resources.json`, ~40 curated), hand-picked official docs
for the most commonly needed skills (`SKILL_RESOURCE_OVERRIDES` in
`services/learning_engine.py`), and a Coursera/YouTube search fallback for
anything not individually curated so every item always has somewhere to
click. **Note:** most of these URLs are stable root-domain links I'm
confident in, but only the AWS and PMP links were individually verified
via search — worth spot-checking the rest periodically since certifying
bodies do restructure their sites occasionally.

**Wording & mistakes tab:** line-by-line writing analysis
(`services/writing_analyzer.py`) flagging weak opening phrases ("Responsible
for...", "Worked on..."), first-person pronouns, overlong bullets, and
likely typos. Clicking a flagged line jumps straight to it in the resume
editor and selects it — this is the "lines they can edit" piece: the tool
never auto-rewrites your resume, it points at the exact spot and gets out
of the way.

Typo detection uses `pyspellchecker`, filtered against every skill name in
the database (so "Kubernetes" or "Terraform" never get flagged) plus a
manual filter for two PDF-extraction artifacts that would otherwise look
like tool bugs: words with a capital letter *mid-word* (a dropped space,
e.g. "inWells" from "in Wells Fargo") and words over 14 characters — both
are almost always merged text from PDF extraction, not something the
candidate actually typed. Deliberately conservative: only lowercase-starting
words are checked at all, to avoid flagging capitalized company/person
names as typos.

**A real performance bug caught during testing:** `pyspellchecker`'s
built-in `.correction()` falls back to an expensive edit-distance-2 search
whenever a word has no close match, which measured at up to 1.5 seconds
*per word* — a single resume pushed total analysis time to ~10 seconds.
Replaced with a cheaper edit-distance-1-only lookup
(`_fast_correction` in `services/writing_analyzer.py`) that skips words
with no close match entirely rather than paying for the expensive search.
This also improved suggestion quality — the distance-2 fallback was
producing bad suggestions like "theDevelopment" → "redevelopment".
Full pipeline (parse → domain detect → score → writing analysis → learning
plan) now measured at 30-55ms per resume, including on re-score.

---

## Running locally

```bash
python3 -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env          # then edit SECRET_KEY
python3 app.py
```

Visit `http://127.0.0.1:5000`.

## Deploying

The app is a standard Flask app with a `Procfile` for Render/Railway/Heroku-style
platforms:

```
web: gunicorn app:app
```

Set the `SECRET_KEY` environment variable on whatever host you use — don't
ship the dev default. `PORT` is read from the environment automatically.

### Before you charge money for this, know the limitations

- **Session storage now scales correctly** as of v6 — see the Redis section
  below. Just don't forget to actually set `REDIS_URL` in production, or
  you're silently back to the single-worker-only in-memory fallback.
- **No auth, no persistence across visits.** Nothing is saved once a session
  expires (6 hours) or Redis evicts it. That's a reasonable privacy
  default, but if you want users to come back and see past analyses, you'll
  need accounts + a real database (Postgres, not Redis — Redis here is
  session cache, not permanent storage).
- **No payment integration.** There's nothing here gating features behind a
  paywall. If you want a free tier + paid tier, that's the next real piece
  of work — happy to help wire up Stripe Checkout when you're ready.
- **Scanned/image-only PDFs aren't supported** — text extraction needs a real
  text layer. Worth an OCR fallback (e.g. Tesseract) if that's common for
  your users.

---

## v6 — Redis-backed sessions (multi-worker support)

**The bug, proven, not just asserted:** `app.py`'s session store was a
plain Python dict. Under gunicorn's pre-fork model, each worker process is
a separate OS process with its own memory — a global dict in worker A is
invisible to worker B. Tested this directly: created 20 sessions under 2
concurrent gunicorn workers, then inspected each worker's own memory —
worker A held 10 of the 20 sessions, worker B held the other 10, completely
split. Any visitor unlucky enough to have their `/analyze` and `/result`
requests land on different workers got bounced back to "please analyze a
resume first" for no visible reason.

**Fixed:** `get_record()`/`save_record()` in `app.py` now write to Redis
(with a 6-hour TTL, matching the old in-memory expiry) when `REDIS_URL` is
set, so every worker reads and writes the same store instead of its own
private memory. Re-ran the identical concurrent test with Redis + 2
workers: 0 failures across 100 session checks, and Redis correctly held
all 20 sessions. If `REDIS_URL` isn't set, it falls back to the old
in-memory dict — fine for local development, but **only correct with
exactly one worker**, same caveat as before.

### Setting up Redis

**Local development:** you don't need to do anything — no `REDIS_URL` set
means it uses the in-memory fallback automatically, same as before.

**Production (Render):**
1. In your Render dashboard: **New → Key Value** (Render's managed Redis).
   Free tier is enough to start.
2. Once created, copy its **Internal Connection String** (looks like
   `redis://red-xxxxx:6379`).
3. On your ResumeIQ web service → Environment → add:
   ```
   REDIS_URL = redis://red-xxxxx:6379
   ```
4. Redeploy. From this point on you can safely increase `--workers` in
   your start command (or Render's instance count) without losing sessions.

**Other hosts:** any Redis works — Railway, Upstash (has a generous free
tier and works well for low-traffic apps), or a self-hosted instance. Just
set `REDIS_URL` to its connection string; nothing else in the code needs
to change.

---

## Project structure

```
app.py                     Routes: upload, analyze, live rescore, PDF download
services/
  parser.py                 Text extraction (PDF/DOCX/TXT) + contact/edu parsing
  ats_engine.py              Orchestrates the full scoring pipeline
  scoring_engine.py          Individual 0-100 component scores
  skill_matcher.py           Skill extraction against data/skills.json
  role_matcher.py            Best-fit role against data/roles.json
  jd_matcher.py               Resume vs. job description skill matching
  analytics_engine.py        Resume health / interview readiness / hiring probability
  recommendation_engine.py   Targeted + general improvement suggestions
  pdf_generator.py           Downloadable PDF report
templates/                  Jinja templates (base, index, result, 404, 500)
static/css/style.css        Design system
static/js/app.js            Upload page (dropzone, JD counter)
static/js/dashboard.js      Live editor: tabs + fetch-based re-scoring
data/                       Skill and role reference data (JSON)
```

## Design

Editorial/document aesthetic on purpose — this is a tool for working on a
document, not a marketing dashboard. Fraunces (serif) for the score number
and headings, Inter for UI text, IBM Plex Mono for scores/tags/data, flat
hairline borders instead of shadows. The signature moment is the score
number itself changing in place (with a `+N`/`-N` delta) the instant you
re-score edited text, rather than a gauge or progress ring.
