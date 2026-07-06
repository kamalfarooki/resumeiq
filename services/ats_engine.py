import re
import difflib

from services.parser import parse_resume

from services.skill_matcher import (
    extract_skills,
    categorize_skills,
    calculate_skill_coverage,
    missing_core_skills,
    recommend_certifications,
    recommend_trending_skills,
    detect_domain
)

from services.role_matcher import (
    match_roles,
    best_role
)

from services.scoring_engine import (
    calculate_scores
)

from services.analytics_engine import (
    build_dashboard
)

from services.recommendation_engine import (
    generate_recommendations,
    generate_recruiter_tips
)

from services.learning_engine import (
    build_learning_plan
)

from services.writing_analyzer import (
    analyze_writing
)

from services.recruiter_score import (
    calculate_recruiter_score,
    generate_rejection_reasons
)

from services.jd_matcher import (
    match_resume_with_jd
)


# ============================================================
# EXPERIENCE LEVEL
# ============================================================

def experience_level(parsed):
    years = parsed.get("experience_years", 0)

    if years >= 15:
        return "Principal"
    elif years >= 10:
        return "Senior"
    elif years >= 6:
        return "Mid-Level"
    elif years >= 3:
        return "Associate"

    return "Entry Level"


# ============================================================
# ROLE-TITLE FALLBACK (used only when skill-based role matching
# in role_matcher.py finds no meaningful overlap at all)
# ============================================================

TITLE_KEYWORDS_BY_DOMAIN = {
    "Information Technology": {
        "Site Reliability Engineer": ["site reliability engineer", "sre"],
        "DevOps Engineer": ["devops engineer", "devops"],
        "Java Developer": ["java developer"],
        "Data Engineer": ["data engineer", "data engineering"],
        "Machine Learning Engineer": ["machine learning engineer", "ml engineer", "ai engineer"],
    },
    "Finance & Accounting": {
        "Finance and Accounts Manager": ["finance and account manager", "finance manager", "accounts manager"],
        "Financial Analyst": ["financial analyst"],
        "Accountant": ["accountant", "senior accountant"],
        "Audit & Compliance Manager": ["audit manager", "compliance manager", "internal auditor"],
    },
    "Sales & Marketing": {
        "Digital Marketing Manager": ["digital marketing manager", "marketing manager"],
        "Sales Manager": ["sales manager", "business development manager"],
        "Marketing Analyst": ["marketing analyst"],
    },
    "Human Resources": {
        "HR Manager": ["hr manager", "human resources manager"],
        "Talent Acquisition Specialist": ["talent acquisition", "recruiter", "recruitment specialist"],
        "HR Business Partner": ["hr business partner", "hrbp"],
    },
    "Healthcare & Nursing": {
        "Registered Nurse": ["registered nurse", "staff nurse"],
        "Clinical Coordinator": ["clinical coordinator", "clinical manager"],
    },
    "Design & Creative": {
        "UI/UX Designer": ["ui/ux designer", "ux designer", "ui designer", "product designer"],
        "Graphic Designer": ["graphic designer"],
    },
    "Legal": {
        "Corporate Lawyer": ["corporate lawyer", "corporate counsel", "attorney"],
        "Paralegal": ["paralegal"],
    },
    "Operations & Supply Chain": {
        "Supply Chain Manager": ["supply chain manager", "supply chain"],
        "Operations Manager": ["operations manager"],
    },
    "Customer Support & Success": {
        "Customer Success Manager": ["customer success manager", "customer success"],
        "Customer Support Specialist": ["customer support specialist", "customer support"],
    },
    "Education & Training": {
        "Teacher": ["teacher", "educator"],
        "Instructional Designer": ["instructional designer"],
    },
}


def detect_role_by_title(text, domain):
    text_l = text.lower()
    candidates = TITLE_KEYWORDS_BY_DOMAIN.get(domain, {})

    best_name, best_score = None, 0
    for role, keywords in candidates.items():
        score = sum(text_l.count(k) for k in keywords)
        if score > best_score:
            best_score, best_name = score, role

    return best_name


# ============================================================
# RESUME SECTION ANALYSIS
#
# Detects whether a resume actually *has* a given section by
# looking for a short header-style line (e.g. "CERTIFICATIONS",
# "Language Skills") rather than searching the whole document
# for a keyword substring — that older approach missed headers
# like "LANGUAGE SKILLS" (no literal "languages") and had no way
# to recognize a "CERTIFICATION & TRAINING" section that listed
# non-IT certifications.
# ============================================================

SECTION_SYNONYMS = {
    "Summary": ["summary", "professional summary", "profile", "objective", "about me"],
    "Skills": ["skills", "technical skills", "core competencies", "key skills", "competencies"],
    "Experience": ["experience", "employment history", "work experience", "professional experience", "work history"],
    "Projects": ["project", "projects", "key projects"],
    "Education": ["education", "academic qualification", "qualifications"],
    "Certifications": ["certification", "certifications", "licenses", "courses & certifications"],
    "Achievements": ["achievement", "achievements", "award", "awards", "honors", "accomplishments"],
    "Languages": ["language", "languages", "language skills", "linguistic skills"],
}


def _is_header_line(line, synonyms):
    clean = line.strip().strip(":•-").strip().lower()
    if not clean or len(clean.split()) > 6:
        return False

    for syn in synonyms:
        if re.search(r"\b" + re.escape(syn) + r"\b", clean):
            return True

    # Fuzzy fallback: resume headers sometimes have typos (e.g. "EXPERICENCE",
    # "ACHEIVEMENT"). A misspelled header is still a header — don't punish the
    # candidate twice for a spelling mistake by also hiding the section.
    # Only single-word synonyms are used here: decomposing multi-word phrases
    # like "language skills" into ["language", "skills"] would let the generic
    # word "skills" fuzzy-match unrelated headers like "Technical Skills".
    words = re.findall(r"[a-z]+", clean)
    single_word_synonyms = [s for s in synonyms if " " not in s and len(s) >= 4]
    for word in words:
        if len(word) < 4:
            continue
        for syn in single_word_synonyms:
            if difflib.SequenceMatcher(None, word, syn).ratio() >= 0.82:
                return True

    return False


def analyze_sections(parsed):
    text = parsed.get("raw_text", "")
    lines = text.splitlines()

    sections = {}
    for name, synonyms in SECTION_SYNONYMS.items():
        sections[name] = any(_is_header_line(line, synonyms) for line in lines)

    # Content-based signals as a fallback/booster: a resume can have real
    # certifications or education listed without a dedicated header.
    if parsed.get("certifications"):
        sections["Certifications"] = True
    if parsed.get("education"):
        sections["Education"] = True

    sections["Contact"] = bool(parsed.get("email")) and bool(parsed.get("phone"))

    return sections


# ============================================================
# MAIN ATS ENGINE
# ============================================================

def analyze_resume(text, jd_text=""):
    """
    Runs the full ATS pipeline on a resume.

    The pipeline first figures out which professional domain the resume
    belongs to (Information Technology, Finance & Accounting, ...) based on
    which domain's skills actually show up in the text, then scopes role
    matching, core-skill gaps, and certification suggestions to that domain
    instead of assuming everyone is a DevOps engineer.

    If jd_text is supplied, also returns a job-description match score
    and a list of keywords missing from the resume relative to that JD.
    """

    # STEP 1 - Parse Resume
    parsed = parse_resume(text)
    parsed["raw_text"] = text

    # STEP 2 - Extract Skills (across every domain at once)
    skills = extract_skills(text)
    categorized = categorize_skills(skills)

    # STEP 3 - Detect Domain
    domain = detect_domain(skills)
    coverage = calculate_skill_coverage(skills, domain)

    # STEP 4 - Detect Sections
    sections = analyze_sections(parsed)

    # STEP 5 - Calculate ATS Score
    scores = calculate_scores(parsed, text, skills, sections, coverage=coverage)
    score = scores["ats_score"]

    # STEP 6 - Career Role Matching (scoped to the detected domain)
    role_matches = match_roles(skills, domain=domain)
    best = best_role(skills, domain=domain)

    if best:
        role = best["role"]
    elif domain:
        role = detect_role_by_title(text, domain) or f"{domain} Professional"
    else:
        role = "Professional"

    # STEP 7 - Skill Intelligence
    missing_core = missing_core_skills(skills, role)
    recommended_certs = recommend_certifications(role)
    trending = recommend_trending_skills(role, skills)
    missing_skills = best["missing"] if best else missing_core

    # STEP 8 - Dashboard Analytics
    dashboard = build_dashboard(parsed, sections, score, coverage)

    # STEP 9 - Job Description Match (optional)
    jd_match = None
    if jd_text and jd_text.strip():
        jd_match = match_resume_with_jd(skills, jd_text)

    # STEP 10 - Build Result
    result = {
        # ATS
        "ats_score": score,
        "grade": (
            "A+" if score >= 90 else
            "A" if score >= 80 else
            "B" if score >= 70 else
            "C" if score >= 60 else
            "D"
        ),

        # Resume
        "candidate": parsed,
        "sections": sections,
        "skills": skills,
        "matched_skills": skills,
        "categorized_skills": categorized,
        "experience_level": experience_level(parsed),

        # Domain & Career
        "domain": domain or "General",
        "detected_role": role,
        "best_role": best,
        "role_matches": role_matches,

        # Skills
        "skill_coverage": coverage,
        "missing_core_skills": missing_core,
        "missing_skills": missing_skills,
        "recommended_certifications": recommended_certs,
        "trending_skills": trending,

        # Job description match
        "jd_match": jd_match,

        # Individual ATS component scores
        "experience_score": scores["experience_score"],
        "education_score": scores["education_score"],
        "certification_score": scores["certification_score"],
        "project_score": scores["project_score"],
        "contact_score": scores["contact_score"],
        "skill_score": scores["skill_score"],
        "length_score": scores["length_score"],
        "section_score": scores["section_score"],

        # Dashboard
        "resume_health": dashboard["resume_health"],
        "interview_readiness": dashboard["interview_readiness"],
        "market_readiness": dashboard["market_readiness"],
        "hiring_probability": dashboard["hiring_probability"],
        "section_completion": dashboard["section_completion"],

        # Word count (useful for the live editor)
        "word_count": len(text.split()),

        # AI Recommendations
        "recommendations": [],
        "recruiter_tips": [],
        "learning_plan": [],
        "writing_issues": [],
        "recruiter_score": {},
        "rejection_reasons": []
    }

    result["recommendations"] = generate_recommendations(result)
    result["recruiter_tips"] = generate_recruiter_tips(result)
    result["learning_plan"] = build_learning_plan(result)
    result["writing_issues"] = analyze_writing(text)
    result["recruiter_score"] = calculate_recruiter_score(result, text)
    result["rejection_reasons"] = generate_rejection_reasons(result, result["recruiter_score"])

    return result
