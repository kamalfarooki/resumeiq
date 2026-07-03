import re

try:
    from spellchecker import SpellChecker
    _SPELL = SpellChecker()
    _SPELLCHECK_AVAILABLE = True
except ImportError:  # pragma: no cover - keeps the app running if the optional dep is missing
    _SPELL = None
    _SPELLCHECK_AVAILABLE = False

from services.skill_matcher import SKILL_DB, ALIASES


# =====================================================
# Vocabulary the spellchecker should never flag: every tracked skill
# name (across all domains) plus common resume/business jargon that
# general-purpose dictionaries often don't recognize.
# =====================================================

def _build_known_terms():
    terms = set()
    for domain in SKILL_DB.values():
        for skills in domain.values():
            for skill in skills:
                for word in re.findall(r"[a-z]+", skill.lower()):
                    terms.add(word)
    for alias in ALIASES:
        for word in re.findall(r"[a-z]+", alias.lower()):
            terms.add(word)
    return terms


_KNOWN_TERMS = _build_known_terms() | {
    "devops", "backend", "frontend", "fullstack", "onboarding", "stakeholders",
    "dashboards", "apis", "api", "saas", "paas", "iaas", "kpis", "kpi",
    "roadmap", "microservices", "containerization", "orchestration",
    "scalability", "latency", "throughput", "uptime", "crm", "erp", "hris",
    "resume", "linkedin", "github", "gitlab", "fintech", "healthtech",
    "edtech", "ecommerce", "onsite", "offsite", "freelance", "remote",
    "hybrid", "runbooks", "postmortems", "blameless", "toil", "sre",
    "autosys", "sla", "slo", "sli", "rca", "bcp", "itil", "middleware",
    "datacenters", "reoccurrences", "webapp", "apac", "emea", "b2b", "b2c",
    "esg", "kyc", "aml", "gdpr", "hipaa", "seo", "sem", "crm's",
}

WEAK_STARTERS = [
    "responsible for", "worked on", "helped with", "involved in",
    "assisted in", "duties included", "tasked with", "in charge of",
    "was responsible", "handled the", "participated in",
]

_FIRST_PERSON_PATTERN = re.compile(r"\b(i|i'm|i've|my|we|our|me)\b", re.IGNORECASE)


def _is_bullet_line(line):
    stripped = line.strip()
    if len(stripped) < 15:
        return False
    word_count = len(stripped.split())
    if word_count < 4 or word_count > 70:
        return False
    return True


def _check_weak_opener(line):
    lowered = line.strip().lstrip("•-*").strip().lower()
    for phrase in WEAK_STARTERS:
        if lowered.startswith(phrase):
            return {
                "type": "weak_opener",
                "title": "Weak opening phrase",
                "message": f'Starts with "{phrase}" — lead with a strong action verb instead (e.g. Led, Built, Automated, Delivered, Reduced).'
            }
    return None


def _check_first_person(line):
    if _FIRST_PERSON_PATTERN.search(line):
        return {
            "type": "first_person",
            "title": "First-person pronoun",
            "message": "Resume bullets are conventionally written without \"I\"/\"my\"/\"we\" — drop the pronoun and start directly with the verb."
        }
    return None


def _check_length(line):
    word_count = len(line.strip().split())
    if word_count > 35:
        return {
            "type": "too_long",
            "title": "Long bullet",
            "message": f"This line is {word_count} words — consider splitting it into two bullets or trimming to the strongest part."
        }
    return None


def _fast_correction(word):
    """
    A deliberately cheaper alternative to SpellChecker.correction().
    .correction() falls back to an expensive edit-distance-2 search
    (candidate generation is O(word_length^2 * 26^2)) whenever there's no
    close match, which can take over a second for a single word — far too
    slow to run across every bullet on every re-score. Distance-2
    "corrections" are also frequently wrong for resume text anyway
    (e.g. "theDevelopment" -> "redevelopment"), so skipping them is a
    net improvement in both speed and suggestion quality.
    """
    close_matches = _SPELL.known(_SPELL.edit_distance_1(word))
    if not close_matches:
        return None
    return max(close_matches, key=lambda w: _SPELL.word_frequency[w])


def _check_spelling(line):
    if not _SPELLCHECK_AVAILABLE:
        return []

    # Only consider words that:
    #  - start lowercase in the original text (filters out proper nouns —
    #    company names, people, places — which are almost always capitalized)
    #  - contain no capital letters at all (a capital *mid-word*, like
    #    "inWells" or "theDevelopment", is a PDF text-extraction artifact
    #    where a space was dropped between two real words — not a typo the
    #    candidate actually made, and not worth flagging)
    #  - are 4-14 characters (longer tokens are usually merged-word
    #    artifacts too, and rarely have a reliable single-edit correction)
    candidates = [
        w for w in re.findall(r"[A-Za-z]+", line)
        if w.islower() and 4 <= len(w) <= 14 and w not in _KNOWN_TERMS
    ]
    if not candidates:
        return []

    unknown = _SPELL.unknown(candidates)
    issues = []
    for word in candidates:
        if word in unknown:
            suggestion = _fast_correction(word)
            if suggestion and suggestion != word:
                issues.append({
                    "type": "spelling",
                    "title": "Possible typo",
                    "message": f'"{word}" might be a typo — did you mean "{suggestion}"?',
                    "original_word": word,
                    "suggested_word": suggestion,
                })
    return issues


def analyze_writing(text, max_issues=25):
    """
    Scans the resume line by line for common resume-writing problems:
    weak openers, first-person pronouns, overlong bullets, and likely
    typos. Returns a flat list capped at max_issues so the UI stays
    scannable rather than overwhelming on a long resume.
    """
    issues = []
    lines = text.splitlines()

    for idx, line in enumerate(lines):
        if not _is_bullet_line(line):
            continue

        line_issues = []
        for check in (_check_weak_opener, _check_first_person, _check_length):
            result = check(line)
            if result:
                line_issues.append(result)
        line_issues.extend(_check_spelling(line))

        for issue in line_issues:
            issues.append({
                "line_number": idx + 1,
                "line_text": line.strip(),
                **issue
            })

        if len(issues) >= max_issues:
            break

    return issues[:max_issues]
