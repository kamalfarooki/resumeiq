import json
import os
import re

# =====================================================
# Load Skills Database (nested: domain -> category -> [skills])
# =====================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL_FILE = os.path.join(BASE_DIR, "data", "skills.json")
ROLE_FILE = os.path.join(BASE_DIR, "data", "roles.json")

with open(SKILL_FILE, "r", encoding="utf-8") as f:
    SKILL_DB = json.load(f)

with open(ROLE_FILE, "r", encoding="utf-8") as f:
    ROLE_DB = json.load(f)


# =====================================================
# Skill Aliases
# Maps a way a skill is commonly written to the canonical
# name used in skills.json, so both forms are recognized.
# =====================================================

ALIASES = {
    "js": "JavaScript",
    "k8s": "Kubernetes",
    "gke": "Google Kubernetes Engine",
    "eks": "AWS EKS",
    "ec2": "AWS EC2",
    "s3": "AWS S3",
    "aws pcf": "PCF",
    "pcf": "PCF",
    "github actions": "GitHub Actions",
    "appd": "AppDynamics",
    "servicenow": "ServiceNow",
    "nginx": "Nginx",

    # Finance & Accounting aliases
    "ms dynamic": "MS Dynamics",
    "sap fico": "SAP FI-CO",
    "sap fi co": "SAP FI-CO",
    "ap/ar": "Accounts Payable",
    "p&l": "P&L Management",
    "profit and loss": "P&L Management",
    "sox": "SOX Compliance",
}


def normalize(text):
    text = text.lower()
    text = re.sub(r"[\r\n\t]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text


# =====================================================
# Flat helpers over the nested SKILL_DB
# =====================================================

def _all_categories():
    """Yields (domain, category, skills_list) for every category in every domain."""
    for domain, categories in SKILL_DB.items():
        for category, skills in categories.items():
            yield domain, category, skills


def domain_names():
    return list(SKILL_DB.keys())


def domain_skill_total(domain):
    if domain not in SKILL_DB:
        return 0
    return sum(len(skills) for skills in SKILL_DB[domain].values())


# =====================================================
# Precompiled patterns
#
# Built once at import time. With ~400 tracked skills across 10 domains,
# compiling a fresh regex per skill on every request would add up —
# precompiling keeps analysis (and re-scoring while editing) fast.
# =====================================================

_SKILL_PATTERNS = [
    (skill, re.compile(r"\b" + re.escape(skill.lower()) + r"\b"))
    for _domain, _category, skills in _all_categories()
    for skill in skills
]

_ALIAS_PATTERNS = [
    (original, re.compile(r"\b" + re.escape(alias.lower()) + r"\b"))
    for alias, original in ALIASES.items()
]


# =====================================================
# Extract Skills (searches every domain at once — a resume
# can legitimately mention skills from more than one)
# =====================================================

def extract_skills(text):
    text = normalize(text)
    found = set()

    for skill, pattern in _SKILL_PATTERNS:
        if pattern.search(text):
            found.add(skill)

    for original, pattern in _ALIAS_PATTERNS:
        if pattern.search(text):
            found.add(original)

    return sorted(found)


# =====================================================
# Categorize Skills — nested by domain so the UI can show
# "Finance & Accounting" and "Information Technology" as
# separate groups when a resume touches both.
# =====================================================

def categorize_skills(skills):
    skill_set = set(skills)
    categorized = {}

    for domain, category, dbskills in _all_categories():
        matched = sorted(skill_set.intersection(dbskills))
        if matched:
            categorized.setdefault(domain, {})[category] = matched

    return categorized


# =====================================================
# Domain Detection
#
# Decides which professional domain a resume belongs to, based
# on how many of that domain's skills actually turned up in it.
# This is what everything else (role matching, core-skill gaps,
# certifications) gets scoped to, instead of assuming IT.
# =====================================================

def detect_domain(skills):
    if not skills:
        return None

    skill_set = set(skills)
    scores = {}

    for domain in SKILL_DB:
        domain_skills = set()
        for cat_skills in SKILL_DB[domain].values():
            domain_skills.update(cat_skills)
        scores[domain] = len(skill_set.intersection(domain_skills))

    best_domain = max(scores, key=scores.get)

    if scores[best_domain] == 0:
        return None

    return best_domain


# =====================================================
# Skill Coverage — relative to the detected domain's own
# skill pool, not the combined total across every domain.
# =====================================================

def calculate_skill_coverage(skills, domain=None):
    if domain is None:
        domain = detect_domain(skills)

    total = domain_skill_total(domain) if domain else sum(
        domain_skill_total(d) for d in SKILL_DB
    )

    if total == 0:
        return 0

    matched_in_domain = skills
    if domain:
        domain_skills = set()
        for cat_skills in SKILL_DB[domain].values():
            domain_skills.update(cat_skills)
        matched_in_domain = [s for s in skills if s in domain_skills]

    coverage = round((len(matched_in_domain) / total) * 100)
    return min(coverage, 100)


# =====================================================
# Missing Core Skills & Recommended Certifications
#
# Both are read straight from roles.json instead of a second,
# separately-maintained list — that duplication is exactly how
# "Data Engineer" ended up with no core-skill list before.
# =====================================================

def missing_core_skills(skills, role):
    role_info = ROLE_DB.get(role)
    if not role_info:
        return []

    required = role_info.get("skills", [])
    return sorted(set(required) - set(skills))


def recommend_certifications(role):
    role_info = ROLE_DB.get(role)
    if not role_info:
        return []
    return role_info.get("certifications", [])


def recommend_trending_skills(role, skills):
    """Skills that are currently in demand for this role and not yet on the resume."""
    role_info = ROLE_DB.get(role)
    if not role_info:
        return []

    trending = role_info.get("trending_skills", [])
    resume_skills_lower = {s.lower() for s in skills}
    return [t for t in trending if t.lower() not in resume_skills_lower]


# =====================================================
# Dashboard Summary
# =====================================================

def skill_summary(skills):
    categorized = categorize_skills(skills)
    return {
        "total_skills": len(skills),
        "categories": sum(len(cats) for cats in categorized.values()),
        "categorized": categorized,
    }
