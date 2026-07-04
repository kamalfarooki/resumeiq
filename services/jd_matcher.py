import re

from services.skill_matcher import extract_skills

STOPWORDS = {
    "the", "and", "for", "with", "you", "your", "our", "are", "will", "have",
    "this", "that", "from", "who", "job", "role", "work", "years", "year",
    "experience", "team", "strong", "ability", "including", "etc", "such",
    "using", "should", "must", "candidate", "candidates", "responsibilities",
    "requirements", "preferred", "plus", "looking", "into", "into", "than",
    "about", "across", "within", "across", "including", "please", "based"
}


def clean(text):
    return re.sub(r"[^a-z0-9 ]", " ", text.lower())


def extract_keywords(text):
    text = clean(text)
    words = [w for w in text.split() if len(w) > 2 and w not in STOPWORDS]
    return list(set(words))


def match_resume_with_jd(resume_skills, jd_text):
    """
    Compares a resume's extracted skills against a job description in two ways:
      1. Skill-level match: which known skills mentioned in the JD are present
         in the resume (this is the most reliable signal).
      2. Keyword coverage: a looser score based on general keyword overlap,
         used only as a secondary signal so the score doesn't look artificially low.
    """

    jd_skills = extract_skills(jd_text)
    resume_skill_set = {s.lower() for s in resume_skills}

    matched_skills = sorted(s for s in jd_skills if s.lower() in resume_skill_set)
    missing_skills = sorted(s for s in jd_skills if s.lower() not in resume_skill_set)

    jd_keywords = extract_keywords(jd_text)
    resume_lower = {s.lower() for s in resume_skills}
    matched_keywords = [w for w in jd_keywords if w in resume_lower]

    if jd_skills:
        skill_match_pct = round(len(matched_skills) / len(jd_skills) * 100)
    else:
        skill_match_pct = 0

    if jd_keywords:
        keyword_match_pct = round(len(matched_keywords) / len(jd_keywords) * 100)
    else:
        keyword_match_pct = 0

    # Weight the reliable skill-level match higher than loose keyword overlap
    match_score = round((skill_match_pct * 0.75) + (keyword_match_pct * 0.25))

    return {
        "match_score": min(match_score, 100),
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "jd_skill_count": len(jd_skills)
    }
