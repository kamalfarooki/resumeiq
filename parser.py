import re
import pdfplumber
from docx import Document


# ----------------------------------------------------
# TEXT EXTRACTION
# ----------------------------------------------------

def extract_text(file_path):
    """Extract raw text from a PDF, DOCX or TXT resume file."""

    lower = file_path.lower()

    if lower.endswith(".pdf"):
        text = ""
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text

    if lower.endswith(".docx"):
        doc = Document(file_path)
        return "\n".join(p.text for p in doc.paragraphs)

    if lower.endswith(".txt"):
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

    return ""


# ----------------------------------------------------
# EMAIL
# ----------------------------------------------------

def extract_email(text):
    match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    return match.group(0) if match else ""


# ----------------------------------------------------
# PHONE
# ----------------------------------------------------

def extract_phone(text):
    match = re.search(r"(\+?\d[\d\s\-]{8,15})", text)
    if match:
        return match.group(1).strip()
    return ""


# ----------------------------------------------------
# LINKEDIN
# ----------------------------------------------------

def extract_linkedin(text):
    match = re.search(r"(linkedin\.com/in/[A-Za-z0-9\-_/]+)", text, re.IGNORECASE)
    if match:
        return match.group(1)

    # Some resumes just list a handle like "@ggeorge84" near a LinkedIn label
    match = re.search(r"linkedin[^\n]{0,40}?@([A-Za-z0-9\-_.]+)", text, re.IGNORECASE)
    if match:
        return f"@{match.group(1)}"

    # PDFs sometimes render only the LinkedIn *icon* (not the word) next to a
    # handle, so the extracted text has no "linkedin" nearby at all — a
    # standalone "@handle" line in the contact block is still a strong signal.
    for line in text.splitlines()[:30]:
        stripped = line.strip()
        if re.fullmatch(r"@[A-Za-z0-9\-_.]{3,30}", stripped):
            return stripped

    return ""


# ----------------------------------------------------
# NAME
# ----------------------------------------------------

def extract_name(text):
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    blacklist = {
        "professional summary", "summary", "experience", "technical skills",
        "education", "skills", "profile", "curriculum vitae", "resume"
    }

    for line in lines[:10]:
        if line.lower() in blacklist:
            continue
        if 0 < len(line.split()) <= 5 and not extract_email(line) and not extract_phone(line):
            return line

    return ""


# ----------------------------------------------------
# EXPERIENCE
# ----------------------------------------------------

def extract_experience(text):
    lower = text.lower()
    years = re.findall(r"(\d+)\+?\s*years", lower)
    if years:
        return max(int(y) for y in years)
    return 0


# ----------------------------------------------------
# EDUCATION
# ----------------------------------------------------

def extract_education(text):
    degrees = [
        "b.tech", "btech", "b.e", "be", "m.tech", "mtech", "mba", "mca",
        "bachelor", "master", "phd", "university", "college"
    ]

    found = []
    lower = text.lower()

    for degree in degrees:
        if re.search(r"\b" + re.escape(degree) + r"\b", lower):
            found.append(degree.upper())

    return sorted(set(found))


# ----------------------------------------------------
# CERTIFICATIONS
# ----------------------------------------------------

def extract_certifications(text):
    # Unambiguous certification acronyms — these aren't also the name of a
    # plain skill/platform, so a bare mention is a safe signal.
    unambiguous_certs = [
        "ITIL", "PMP", "CKA", "CKAD", "RHCE", "ACCA", "CPA", "CFA", "CMA",
        "CIA", "CIMA", "ICWAI", "FRM", "PRINCE2", "SHRM"
    ]

    # Platform/tool names (AWS, Azure, GCP, Terraform...) are ambiguous —
    # merely mentioning "AWS" as a skill isn't the same as holding an AWS
    # certification, so these require a certification-specific phrase.
    specific_phrases = {
        "aws certified": "AWS",
        "aws solutions architect": "AWS Solutions Architect",
        "azure fundamentals": "Azure Fundamentals",
        "azure administrator": "Azure Administrator",
        "google cloud certified": "GCP",
        "gcp certified": "GCP",
        "terraform associate": "Terraform Associate",
        "six sigma": "Six Sigma",
    }

    # Full names people spell out instead of using the acronym.
    phrase_aliases = {
        "association of chartered certified accountants": "ACCA",
        "chartered financial analyst": "CFA",
        "certified public accountant": "CPA",
        "certified management accountant": "CMA",
        "certified internal auditor": "CIA",
        "chartered accountant": "CA",
    }

    found = []
    lower = text.lower()

    for cert in unambiguous_certs:
        pattern = r"\b" + re.escape(cert.lower()) + r"\b"
        if re.search(pattern, lower):
            found.append(cert)

    for phrase, cert in specific_phrases.items():
        if phrase in lower:
            found.append(cert)

    for phrase, cert in phrase_aliases.items():
        if phrase in lower:
            found.append(cert)

    return sorted(set(found))


# ----------------------------------------------------
# PARSE RESUME
# ----------------------------------------------------

def parse_resume(text):
    return {
        "name": extract_name(text),
        "email": extract_email(text),
        "phone": extract_phone(text),
        "linkedin": extract_linkedin(text),
        "experience_years": extract_experience(text),
        "education": extract_education(text),
        "certifications": extract_certifications(text),
        "raw_text": text
    }
