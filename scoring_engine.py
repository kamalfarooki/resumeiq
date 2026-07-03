import math


# =====================================================
# Experience Score
# =====================================================

def experience_score(parsed):

    years = parsed.get("experience_years", 0)

    if years >= 15:
        return 20

    elif years >= 10:
        return 18

    elif years >= 7:
        return 16

    elif years >= 5:
        return 14

    elif years >= 3:
        return 10

    elif years >= 1:
        return 6

    return 2


# =====================================================
# Education Score
# =====================================================

def education_score(parsed):

    education = " ".join(
        parsed.get("education", [])
    ).lower()

    if "phd" in education:
        return 10

    if "master" in education or "mca" in education or "mba" in education:

        return 9

    if "bachelor" in education or "b.tech" in education or "be" in education:

        return 8

    return 4


# =====================================================
# Certification Score
# =====================================================

def certification_score(parsed):

    certs = parsed.get(
        "certifications",
        []
    )

    if len(certs) >= 5:
        return 10

    if len(certs) >= 3:
        return 8

    if len(certs) >= 1:
        return 6

    return 0


# =====================================================
# Project Score
# =====================================================

def project_score(text):

    projects = text.lower().count("project")

    if projects >= 5:
        return 10

    if projects >= 3:
        return 8

    if projects >= 1:
        return 6

    return 2


# =====================================================
# Contact Score
# =====================================================

def contact_score(parsed):

    score = 0

    if parsed.get("email"):
        score += 3

    if parsed.get("phone"):
        score += 2

    return score


# =====================================================
# Skill Score
#
# Scored against coverage of the *detected domain's* skill pool
# rather than a raw skill count. A raw count unfairly penalizes
# domains with smaller reference skill lists (e.g. Finance has
# ~47 tracked skills vs. IT's ~150) — someone who matches 90% of
# their own domain's relevant skills should score well regardless
# of which domain that is.
# =====================================================

def skill_score(coverage):
    if coverage >= 70:
        return 35
    elif coverage >= 55:
        return 30
    elif coverage >= 40:
        return 25
    elif coverage >= 25:
        return 20
    elif coverage >= 10:
        return 12

    return 6


# =====================================================
# Resume Length
# =====================================================

def length_score(text):

    words = len(text.split())

    if 400 <= words <= 900:
        return 10

    if 300 <= words <= 1200:
        return 8

    return 5


# =====================================================
# Section Score
# =====================================================

def section_score(sections):

    present = sum(
        sections.values()
    )

    total = len(sections)

    return round(
        (present / total) * 10
    )


# =====================================================
# FINAL ATS SCORE
# =====================================================

def calculate_scores(
        parsed,
        text,
        skills,
        sections,
        coverage=0
):

    scores = {

        "experience_score":
            experience_score(parsed),

        "education_score":
            education_score(parsed),

        "certification_score":
            certification_score(parsed),

        "project_score":
            project_score(text),

        "contact_score":
            contact_score(parsed),

        "skill_score":
            skill_score(coverage),

        "length_score":
            length_score(text),

        "section_score":
            section_score(sections)

    }

    total = sum(scores.values())

    ats = min(
        round((total / 110) * 100),
        100
    )

    scores["ats_score"] = ats

    return scores