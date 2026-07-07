from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import inch


def create_pdf(data, filepath):
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(filepath, topMargin=0.6 * inch, bottomMargin=0.6 * inch)
    story = []

    story.append(Paragraph("ResumeIQ Analysis Report", styles["Title"]))
    candidate_name = data.get("candidate", {}).get("name") or "Candidate"
    story.append(Paragraph(candidate_name, styles["Heading3"]))
    story.append(Spacer(1, 12))

    summary_table = Table([
        ["ATS Score", f"{data['ats_score']}%"],
        ["Grade", data["grade"]],
        ["Resume Health", f"{data['resume_health']}%"],
        ["Interview Readiness", data["interview_readiness"]],
        ["Detected Role", data.get("detected_role", "-")],
        ["Experience Level", data.get("experience_level", "-")],
    ], colWidths=[2.5 * inch, 3 * inch])

    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eef2ff")),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#1e293b")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))

    story.append(summary_table)
    story.append(Spacer(1, 20))

    if data.get("recruiter_score"):
        rs = data["recruiter_score"]
        story.append(Paragraph("Recruiter Score", styles["Heading2"]))
        story.append(Paragraph(
            f"<b>{rs['score']}/100 — {rs['label']}</b>",
            styles["Normal"]
        ))
        story.append(Paragraph(
            "A different question from the ATS score: would a human skimming for a few seconds keep reading?",
            styles["Normal"]
        ))
        story.append(Spacer(1, 8))

        if data.get("rejection_reasons"):
            story.append(Paragraph("Why You'd Get Rejected", styles["Heading3"]))
            for reason in data["rejection_reasons"]:
                severity = reason.get("severity", "")
                text = reason.get("reason", "")
                story.append(Paragraph(f"<b>[{severity}]</b> {text}", styles["Normal"]))
                story.append(Spacer(1, 4))
        story.append(Spacer(1, 16))

    story.append(Paragraph("Technical Skills", styles["Heading2"]))
    skills = ", ".join(data.get("skills", [])) or "No skills detected"
    story.append(Paragraph(skills, styles["Normal"]))
    story.append(Spacer(1, 16))

    if data.get("jd_match"):
        jd = data["jd_match"]
        story.append(Paragraph("Job Description Match", styles["Heading2"]))
        story.append(Paragraph(f"Match Score: {jd['match_score']}%", styles["Normal"]))
        if jd.get("missing_skills"):
            story.append(Paragraph(
                "Missing skills: " + ", ".join(jd["missing_skills"][:15]),
                styles["Normal"]
            ))
        story.append(Spacer(1, 16))

    if data.get("trending_skills"):
        story.append(Paragraph("Trending Skills For This Role", styles["Heading2"]))
        story.append(Paragraph(", ".join(data["trending_skills"]), styles["Normal"]))
        story.append(Spacer(1, 16))

    story.append(Paragraph("Resume Sections", styles["Heading2"]))
    for section, status in data.get("sections", {}).items():
        state = "Present" if status else "Missing"
        story.append(Paragraph(f"{section}: {state}", styles["Normal"]))
    story.append(Spacer(1, 16))

    story.append(Paragraph("Recommendations", styles["Heading2"]))
    for item in data.get("recommendations", []):
        title = item.get("title", "")
        message = item.get("message", "")
        priority = item.get("priority", "")
        story.append(Paragraph(f"<b>[{priority}] {title}:</b> {message}", styles["Normal"]))
        story.append(Spacer(1, 4))
    story.append(Spacer(1, 12))

    if data.get("recruiter_tips"):
        story.append(Paragraph("Recruiter Visibility Tips", styles["Heading2"]))
        for item in data["recruiter_tips"]:
            title = item.get("title", "")
            message = item.get("message", "")
            story.append(Paragraph(f"<b>{title}:</b> {message}", styles["Normal"]))
            story.append(Spacer(1, 4))

    doc.build(story)
