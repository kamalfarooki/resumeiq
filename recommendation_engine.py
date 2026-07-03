GENERAL_TIPS = [
    {
        "title": "LinkedIn",
        "message": "Include your LinkedIn profile URL."
    },
    {
        "title": "GitHub",
        "message": "Include your GitHub profile if you have technical projects."
    },
    {
        "title": "Action Verbs",
        "message": "Use strong action verbs like Designed, Led, Automated, Optimized and Implemented."
    },
    {
        "title": "Quantify Achievements",
        "message": "Use numbers to demonstrate business impact (e.g. Reduced incidents by 40%)."
    },
    {
        "title": "ATS Formatting",
        "message": "Avoid tables, images and excessive graphics to improve ATS compatibility."
    },
    {
        "title": "Tailor Resume",
        "message": "Customize your resume for each job application using the JD Match tool."
    },
]


def generate_recruiter_tips(result):
    """
    Tips specifically about getting *found and shortlisted* by recruiters —
    distinct from the ATS-structure recommendations above. Mixes a couple
    of universal, evergreen tips with a couple that react to this resume.
    """
    import re as _re

    tips = []
    candidate = result.get("candidate", {})
    resume_text = candidate.get("raw_text", "")
    role = result.get("detected_role", "your target role")

    if not candidate.get("linkedin"):
        tips.append({
            "title": "Add your LinkedIn URL",
            "message": "Most recruiters check LinkedIn before responding to a resume. Add the full profile URL next to your contact details."
        })

    has_numbers = bool(_re.search(r"\d+%|\$\d|\b\d+\s*(x|times)\b", resume_text.lower()))
    if not has_numbers:
        tips.append({
            "title": "Quantify your impact",
            "message": "Add at least one number to each role — a percentage, dollar figure, team size, or time saved. Resumes with quantified results consistently get more recruiter callbacks than ones with only task descriptions."
        })

    tips.append({
        "title": "Mirror the job title exactly",
        "message": f"Use your target title verbatim (e.g. \"{role}\") in your summary or headline. Recruiters and ATS systems often search by exact title match, not just skills."
    })

    tips.append({
        "title": "Match job posting keywords exactly",
        "message": "Paste a job description into the JD Match tab and add its exact-wording skills to your resume where true — ATS keyword filters are frequently literal, not semantic."
    })

    trending = result.get("trending_skills") or []
    if trending:
        tips.append({
            "title": f"Stay current for {role}",
            "message": "Recruiters searching for this role increasingly filter for: " + ", ".join(trending[:4]) + ". Add any of these you genuinely have experience with."
        })

    return tips


def generate_recommendations(result):
    """
    Returns a prioritized list of *targeted* recommendations based on gaps
    actually found in this resume. General best-practice tips are kept
    separately in GENERAL_TIPS and rendered in their own section.
    """

    recommendations = []
    sections = result["sections"]
    skills = result["skills"]

    if result["ats_score"] < 80:
        recommendations.append({
            "priority": "High",
            "title": "Improve ATS Score",
            "message": "Tailor your resume to the job description by adding relevant keywords."
        })

    if not sections["Summary"]:
        recommendations.append({
            "priority": "High",
            "title": "Professional Summary",
            "message": "Add a strong 3-5 line professional summary highlighting your experience and expertise."
        })

    if not sections["Contact"]:
        recommendations.append({
            "priority": "High",
            "title": "Contact Information",
            "message": "Ensure your email address and mobile number are included."
        })

    if not sections["Education"]:
        recommendations.append({
            "priority": "High",
            "title": "Education Section",
            "message": "Include your educational qualifications and degree details."
        })

    if not sections["Projects"]:
        if result.get("domain") == "Finance & Accounting":
            recommendations.append({
                "priority": "Medium",
                "title": "Key Initiatives",
                "message": "Include 2-3 specific initiatives you led (e.g. a process automation, cost-saving drive, or audit turnaround) with measurable outcomes."
            })
        else:
            recommendations.append({
                "priority": "High",
                "title": "Projects",
                "message": "Include 2-3 projects demonstrating measurable business impact."
            })

    if not sections["Certifications"]:
        cert_hint = ""
        if result.get("recommended_certifications"):
            cert_hint = " (" + ", ".join(result["recommended_certifications"][:3]) + " are common for this role)"
        recommendations.append({
            "priority": "Medium",
            "title": "Certifications",
            "message": f"Add relevant industry certifications{cert_hint}."
        })

    if not sections["Achievements"]:
        recommendations.append({
            "priority": "Medium",
            "title": "Achievements",
            "message": "Add awards, recognitions or measurable accomplishments."
        })

    if len(skills) < 10:
        recommendations.append({
            "priority": "Medium",
            "title": "Technical Skills",
            "message": "Add more technologies relevant to your target role."
        })

    if result["length_score"] < 10:
        word_count = result.get("word_count", 0)
        if word_count and word_count < 400:
            msg = f"Your resume is only {word_count} words. Aim for approximately 400-900 words."
        elif word_count:
            msg = f"Your resume is {word_count} words, which is longer than ideal. Aim for approximately 400-900 words."
        else:
            msg = "Aim for approximately 400-900 words."
        recommendations.append({
            "priority": "Medium",
            "title": "Resume Length",
            "message": msg
        })

    if result["experience_score"] < 15:
        recommendations.append({
            "priority": "Medium",
            "title": "Experience",
            "message": "Expand your work experience with measurable achievements."
        })

    if not sections["Languages"]:
        recommendations.append({
            "priority": "Low",
            "title": "Languages",
            "message": "Mention languages you speak if applicable."
        })

    # JD-specific gap (only shown when a job description was provided)
    jd_match = result.get("jd_match")
    if jd_match and jd_match.get("missing_skills"):
        top_missing = ", ".join(jd_match["missing_skills"][:6])
        recommendations.append({
            "priority": "High",
            "title": "Missing Skills for This Job",
            "message": f"The job description mentions these skills that aren't in your resume: {top_missing}."
        })

    if len(recommendations) == 0:
        recommendations.append({
            "priority": "Info",
            "title": "Excellent Resume",
            "message": "Your resume is well structured and ATS friendly."
        })

    # Sort so High priority items surface first
    order = {"High": 0, "Medium": 1, "Low": 2, "Info": 3}
    recommendations.sort(key=lambda r: order.get(r["priority"], 4))

    return recommendations
