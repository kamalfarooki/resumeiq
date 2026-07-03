import json
import os


# ==========================================================
# Load Role Database
# ==========================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROLE_FILE = os.path.join(BASE_DIR, "data", "roles.json")

with open(ROLE_FILE, "r", encoding="utf-8") as f:
    ROLE_DB = json.load(f)


# ==========================================================
# Match Resume Against Roles
#
# If `domain` is given, only roles tagged with that domain are
# considered — this is what stops a Finance resume from being
# scored against "Site Reliability Engineer".
# ==========================================================

def match_roles(skills, domain=None):
    results = []
    resume_skills = set(skills)

    for role, details in ROLE_DB.items():
        if domain and details.get("domain") != domain:
            continue

        required = set(details["skills"])
        matched = sorted(resume_skills & required)
        missing = sorted(required - resume_skills)

        coverage = round((len(matched) / len(required)) * 100) if required else 0

        results.append({
            "role": role,
            "domain": details.get("domain"),
            "coverage": coverage,
            "matched": matched,
            "missing": missing,
            "recommended_certifications": details.get("certifications", [])
        })

    results.sort(key=lambda x: x["coverage"], reverse=True)
    return results


# ==========================================================
# Best Matching Role
#
# Returns None (rather than an arbitrary 0%-coverage role) when
# nothing in the domain actually matches, so callers can fall
# back honestly instead of asserting a wrong specific title.
# ==========================================================

def best_role(skills, domain=None):
    matches = match_roles(skills, domain=domain)

    if matches and matches[0]["coverage"] > 0:
        return matches[0]

    return None
