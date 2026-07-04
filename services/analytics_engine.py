# ==========================================================
# Resume Health
# ==========================================================

def resume_health(ats_score):

    if ats_score >= 90:
        return 98

    elif ats_score >= 80:
        return 90

    elif ats_score >= 70:
        return 82

    elif ats_score >= 60:
        return 72

    return 60


# ==========================================================
# Interview Readiness
# ==========================================================

def interview_readiness(ats_score):

    if ats_score >= 90:
        return "Excellent"

    elif ats_score >= 80:
        return "High"

    elif ats_score >= 70:
        return "Good"

    elif ats_score >= 60:
        return "Average"

    return "Needs Improvement"


# ==========================================================
# Market Readiness
# ==========================================================

def market_readiness(
        skill_coverage,
        ats_score
):

    value = round(

        (skill_coverage * 0.40) +

        (ats_score * 0.60)

    )

    return min(value, 100)


# ==========================================================
# Hiring Probability
# ==========================================================

def hiring_probability(
        ats_score,
        experience_years
):

    probability = (

        ats_score * 0.75 +

        min(experience_years, 15) * 1.5

    )

    return min(
        round(probability),
        100
    )


# ==========================================================
# Dashboard Builder
# ==========================================================

def build_dashboard(

        parsed,

        sections,

        ats_score,

        skill_coverage

):

    dashboard = {

        "resume_health":

            resume_health(
                ats_score
            ),

        "interview_readiness":

            interview_readiness(
                ats_score
            ),

        "market_readiness":

            market_readiness(

                skill_coverage,

                ats_score

            ),

        "hiring_probability":

            hiring_probability(

                ats_score,

                parsed.get(
                    "experience_years",
                    0
                )

            ),

        "section_completion":

            round(

                sum(
                    sections.values()
                )

                /

                len(sections)

                *

                100

            )

    }

    return dashboard