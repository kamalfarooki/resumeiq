import json
import os
from urllib.parse import quote

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEARNING_FILE = os.path.join(BASE_DIR, "data", "learning_resources.json")

with open(LEARNING_FILE, "r", encoding="utf-8") as f:
    CERT_RESOURCES = json.load(f)


# =====================================================
# A modest set of hand-picked official/primary resources for the
# skills people most commonly need to learn. Not exhaustive — anything
# not listed here falls back to a generated Coursera/YouTube search
# link, which is always valid even if less precisely targeted.
# =====================================================

SKILL_RESOURCE_OVERRIDES = {
    "Kubernetes": {"name": "Kubernetes — Official Tutorials", "url": "https://kubernetes.io/docs/tutorials/"},
    "Docker": {"name": "Docker — Get Started Guide", "url": "https://docs.docker.com/get-started/"},
    "Terraform": {"name": "HashiCorp — Terraform Tutorials", "url": "https://developer.hashicorp.com/terraform/tutorials"},
    "AWS": {"name": "AWS — Getting Started", "url": "https://aws.amazon.com/getting-started/"},
    "Azure": {"name": "Microsoft Learn — Azure Fundamentals", "url": "https://learn.microsoft.com/training/azure/"},
    "GCP": {"name": "Google Cloud Skills Boost", "url": "https://www.cloudskillsboost.google/"},
    "Python": {"name": "Python — Official Tutorial", "url": "https://docs.python.org/3/tutorial/"},
    "SQL": {"name": "Mode — SQL Tutorial", "url": "https://mode.com/sql-tutorial/"},
    "Git": {"name": "Git — Official Documentation", "url": "https://git-scm.com/doc"},
    "Ansible": {"name": "Ansible — Getting Started", "url": "https://docs.ansible.com/ansible/latest/getting_started/index.html"},
    "Jenkins": {"name": "Jenkins — Official Tutorials", "url": "https://www.jenkins.io/doc/tutorials/"},
    "Prometheus": {"name": "Prometheus — Official Docs", "url": "https://prometheus.io/docs/introduction/overview/"},
    "Grafana": {"name": "Grafana — Official Tutorials", "url": "https://grafana.com/tutorials/"},
    "Machine Learning": {"name": "Google — Machine Learning Crash Course", "url": "https://developers.google.com/machine-learning/crash-course"},
    "Generative AI": {"name": "Google Cloud — Generative AI Learning Path", "url": "https://www.cloudskillsboost.google/paths/118"},
    "Power BI": {"name": "Microsoft Learn — Power BI", "url": "https://learn.microsoft.com/training/powerplatform/power-bi"},
    "Advanced Excel": {"name": "Microsoft Support — Excel Training", "url": "https://support.microsoft.com/en-us/excel"},
    "SAP": {"name": "SAP Learning", "url": "https://learning.sap.com/"},
    "Salesforce": {"name": "Salesforce Trailhead", "url": "https://trailhead.salesforce.com/"},
    "Figma": {"name": "Figma — Official Tutorials", "url": "https://help.figma.com/hc/en-us/categories/360002042553-Getting-Started"},
    "Google Analytics 4": {"name": "Google Skillshop — Analytics", "url": "https://skillshop.withgoogle.com/"},
    "SEO": {"name": "Google Search Central — SEO Starter Guide", "url": "https://developers.google.com/search/docs/fundamentals/seo-starter-guide"},
    "HRIS": {"name": "SHRM — HR Technology Resources", "url": "https://www.shrm.org/"},
    "IFRS": {"name": "IFRS Foundation", "url": "https://www.ifrs.org/"},
    "GAAP": {"name": "FASB — GAAP Standards", "url": "https://www.fasb.org/"},
    "Financial Modelling": {"name": "CFI — Financial Modeling Resources", "url": "https://corporatefinanceinstitute.com/resources/financial-modeling/"},
    "Six Sigma": {"name": "ASQ — Six Sigma Resources", "url": "https://asq.org/quality-resources/six-sigma"},
    "Zendesk": {"name": "Zendesk Training & Certification", "url": "https://www.zendesk.com/service/training-certification/"},
    "LMS": {"name": "EDUCAUSE — Learning Management Systems", "url": "https://www.educause.edu/"},
}


def _fallback_resources(skill_name):
    query = quote(skill_name)
    return [
        {"name": f"Search Coursera for \"{skill_name}\"", "url": f"https://www.coursera.org/search?query={query}"},
        {"name": f"Search YouTube for \"{skill_name}\" tutorial", "url": f"https://www.youtube.com/results?search_query={quote(skill_name + ' tutorial')}"},
    ]


def resources_for_skill(skill_name):
    if skill_name in SKILL_RESOURCE_OVERRIDES:
        return [SKILL_RESOURCE_OVERRIDES[skill_name]]
    if skill_name in CERT_RESOURCES:
        return [CERT_RESOURCES[skill_name]]
    return _fallback_resources(skill_name)


def resources_for_certification(cert_name):
    if cert_name in CERT_RESOURCES:
        return [CERT_RESOURCES[cert_name]]
    return _fallback_resources(cert_name + " certification")


# =====================================================
# Build the full learning plan for a resume: what to learn, why,
# and where. Capped so the tab stays focused rather than overwhelming.
# =====================================================

def build_learning_plan(result, max_items=10):
    plan = []
    seen = set()

    for cert in result.get("recommended_certifications", []):
        if cert in seen:
            continue
        seen.add(cert)
        plan.append({
            "title": cert,
            "reason": f"Recommended certification for {result.get('detected_role', 'your role')}.",
            "resources": resources_for_certification(cert)
        })

    for skill in result.get("trending_skills", []):
        if skill in seen:
            continue
        seen.add(skill)
        plan.append({
            "title": skill,
            "reason": f"Currently in demand for {result.get('detected_role', 'your role')} — not yet on your resume.",
            "resources": resources_for_skill(skill)
        })

    for skill in result.get("missing_core_skills", []):
        if skill in seen:
            continue
        seen.add(skill)
        plan.append({
            "title": skill,
            "reason": f"Core skill most {result.get('detected_role', 'candidates in this role')} resumes include.",
            "resources": resources_for_skill(skill)
        })

    return plan[:max_items]
