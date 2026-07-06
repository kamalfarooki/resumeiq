import re

from services.writing_analyzer import extract_bullets


# =====================================================
# Strong action verbs vs. duty language
#
# A bullet starting with one of these reads as "here's what I achieved."
# A bullet starting with a weak opener (see writing_analyzer.WEAK_STARTERS)
# reads as "here's what my job description said." Recruiters notice the
# difference far more than ATS keyword-matching does.
# =====================================================

STRONG_ACTION_VERBS = {
    "led", "built", "launched", "drove", "increased", "reduced", "decreased",
    "saved", "grew", "delivered", "automated", "designed", "implemented",
    "architected", "optimized", "spearheaded", "established", "negotiated",
    "streamlined", "transformed", "migrated", "scaled", "mentored",
    "directed", "managed", "executed", "achieved", "generated", "improved",
    "resolved", "pioneered", "restructured", "accelerated", "cut", "boosted",
    "exceeded", "overhauled", "championed", "created", "developed",
    "engineered", "coordinated", "consolidated", "modernized", "expanded",
    "secured", "authored", "launched", "revamped", "unified", "cultivated",
}

QUANT_PATTERN = re.compile(r"\d+%|\$\d|\b\d{2,}\b")


def _first_word(bullet):
    cleaned = bullet.strip().lstrip("•-*").strip()
    if not cleaned:
        return ""
    word = cleaned.split(" ")[0].strip(".,;:()")
    return word.lower()


def _is_quantified(bullet):
    return bool(QUANT_PATTERN.search(bullet))


def _is_strong_opener(bullet):
    return _first_word(bullet) in STRONG_ACTION_VERBS


# =====================================================
# Recruiter Score
#
# Deliberately different from the ATS score — an ATS cares about keyword
# and structure matching, but a human skimming for ~7 seconds cares about
# a different set of signals: can they tell what you actually did (vs.
# your team), is there any evidence of scale/impact, and is it clean
# enough to not raise doubts before they've even read your experience.
# =====================================================

def calculate_recruiter_score(result, resume_text):
    bullets = extract_bullets(resume_text)
    bullet_count = len(bullets)
    denom = bullet_count or 1  # avoid division by zero; bullet_count itself is reported separately

    quantified_bullets = sum(1 for b in bullets if _is_quantified(b))
    strong_verb_bullets = sum(1 for b in bullets if _is_strong_opener(b))

    quant_rate = quantified_bullets / denom
    strong_rate = strong_verb_bullets / denom

    quant_score = round(quant_rate * 30)
    achievement_score = round(strong_rate * 25)

    issues = result.get("writing_issues", [])
    issue_density = min(len(issues) / denom, 1)
    clarity_score = round((1 - issue_density) * 20)

    sections = result.get("sections", {})
    structure_checks = [
        sections.get("Summary"),
        sections.get("Experience"),
        sections.get("Education"),
        sections.get("Contact"),
    ]
    structure_score = round(sum(1 for c in structure_checks if c) / len(structure_checks) * 15)

    # Reuses the same 0-10 length score the ATS pipeline already computed,
    # since "is this a reasonable length" is the same question either way.
    length_component = result.get("length_score", 0)

    total = quant_score + achievement_score + clarity_score + structure_score + length_component
    total = max(0, min(total, 100))

    if total >= 85:
        label = "Strong Candidate"
    elif total >= 70:
        label = "Competitive"
    elif total >= 55:
        label = "Needs Work"
    elif total >= 40:
        label = "Weak"
    else:
        label = "High Risk of Rejection"

    return {
        "score": total,
        "label": label,
        "bullet_count": bullet_count,
        "quantified_bullets": quantified_bullets,
        "strong_verb_bullets": strong_verb_bullets,
        "components": {
            "Quantified impact": {"value": quant_score, "max": 30},
            "Achievement language": {"value": achievement_score, "max": 25},
            "Clarity & polish": {"value": clarity_score, "max": 20},
            "Resume structure": {"value": structure_score, "max": 15},
            "Length": {"value": length_component, "max": 10},
        },
    }


# =====================================================
# "Why You'd Get Rejected"
#
# Blunt, specific reasons framed the way a recruiter would actually think
# them — not softened resume-tool language. Grounded entirely in signals
# already computed elsewhere in the pipeline, not a separate guess.
# =====================================================

def generate_rejection_reasons(result, recruiter_result):
    reasons = []
    sections = result.get("sections", {})
    bullet_count = recruiter_result["bullet_count"] or 1

    if not sections.get("Contact"):
        reasons.append({
            "severity": "High",
            "reason": "No way to reach you — missing phone number or email address."
        })

    if not sections.get("Summary"):
        reasons.append({
            "severity": "High",
            "reason": "No summary — I don't know what role you're targeting in the first five seconds of reading."
        })

    if result.get("domain") in (None, "General"):
        reasons.append({
            "severity": "High",
            "reason": "I can't tell what role or field you're even applying for from this resume."
        })

    quant_rate = recruiter_result["quantified_bullets"] / bullet_count
    if quant_rate < 0.2:
        reasons.append({
            "severity": "High",
            "reason": f"Only {recruiter_result['quantified_bullets']} of your {bullet_count} bullets include a specific number — the rest read as duties without a measurable outcome."
        })

    strong_rate = recruiter_result["strong_verb_bullets"] / bullet_count
    if strong_rate < 0.25:
        reasons.append({
            "severity": "Medium",
            "reason": f"Only {recruiter_result['strong_verb_bullets']} of your {bullet_count} bullets open with a strong action verb — most read as a list of duties, not what you personally achieved."
        })

    typo_count = sum(1 for i in result.get("writing_issues", []) if i.get("type") == "spelling")
    if typo_count > 0:
        plural = "s" if typo_count > 1 else ""
        reasons.append({
            "severity": "Medium",
            "reason": f"Found {typo_count} likely typo{plural} — raises questions about attention to detail before I've read your experience."
        })

    missing = result.get("missing_core_skills") or []
    if len(missing) >= 3:
        skills = ", ".join(missing[:4])
        role = result.get("detected_role", "this role")
        reasons.append({
            "severity": "Medium",
            "reason": f"Missing skills I'd expect for {role}: {skills}."
        })

    word_count = result.get("word_count", 0)
    if word_count and word_count < 300:
        reasons.append({
            "severity": "Medium",
            "reason": f"Too thin at {word_count} words — not enough here to actually evaluate you on."
        })
    elif word_count and word_count > 900:
        reasons.append({
            "severity": "Low",
            "reason": f"Too long at {word_count} words — most recruiters spend well under a minute on a first pass."
        })

    first_person_count = sum(1 for i in result.get("writing_issues", []) if i.get("type") == "first_person")
    if first_person_count > 0:
        reasons.append({
            "severity": "Low",
            "reason": "Written in first person in places — unconventional for a resume and reads less polished."
        })

    if not sections.get("Certifications") and result.get("recommended_certifications"):
        certs = ", ".join(result["recommended_certifications"][:2])
        reasons.append({
            "severity": "Low",
            "reason": f"No certifications listed — puts you a step behind candidates who have {certs}."
        })

    order = {"High": 0, "Medium": 1, "Low": 2}
    reasons.sort(key=lambda r: order.get(r["severity"], 3))

    if not reasons:
        reasons.append({
            "severity": "Info",
            "reason": "Nothing obvious jumps out — this is a well-structured resume. Your real competition now is being one of hundreds of applicants, not a resume flaw."
        })

    return reasons[:6]
