import os
import sys
import django
import re
from collections import defaultdict
from datetime import datetime

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aetheris_core.settings")
django.setup()


from vtagent.models import RawArticle, GeneratedTaxonomyLabel
from syntheticcmdb.models import ConfigurationItem
from syntheticemployees.models import Employee
from syntheticad.models import ADUser


def extract_keywords(content, keyword_list):
    matches = []
    for keyword in keyword_list:
        if re.search(rf"\b{re.escape(keyword)}\b", content, re.IGNORECASE):
            matches.append(keyword)
    return list(set(matches))


def infer_severity(content):
    if any(w in content.lower() for w in ["critical", "rce", "remote code execution", "zero-day"]):
        return ["Critical"]
    if any(w in content.lower() for w in ["high", "exploit", "elevation of privilege"]):
        return ["High"]
    if any(w in content.lower() for w in ["medium", "vulnerability", "bypass"]):
        return ["Medium"]
    return ["Low"]


def infer_impact(content):
    impact_tags = {
        "data breach": ["data leak", "personal info", "pwned", "compromised records"],
        "service disruption": ["downtime", "outage", "denial of service", "dos"],
        "privilege escalation": ["privilege escalation", "admin access", "root access"]
    }
    matched = []
    for tag, keywords in impact_tags.items():
        for k in keywords:
            if k in content.lower():
                matched.append(tag)
                break
    return matched or ["unknown"]


def infer_actor(content):
    if "insider" in content.lower():
        return ["Insider"]
    if any(term in content.lower() for term in ["apt", "state-sponsored", "russia", "china", "iran"]):
        return ["Nation-State"]
    if any(term in content.lower() for term in ["hacker", "threat actor", "cybercriminal"]):
        return ["Cybercriminal"]
    return ["Unknown"]


def infer_origin(content):
    if any(term in content.lower() for term in ["internal network", "employee", "insider"]):
        return ["Internal"]
    return ["External"]


def infer_compliance(content):
    tags = []
    if "gdpr" in content.lower():
        tags.append("GDPR")
    if "hipaa" in content.lower():
        tags.append("HIPAA")
    if "pci" in content.lower():
        tags.append("PCI-DSS")
    return tags or ["None"]


def generate_taxonomy():
    existing_ids = set(GeneratedTaxonomyLabel.objects.values_list("raw_article_id", flat=True))
    raw_articles = RawArticle.objects.exclude(id__in=existing_ids)

    if not raw_articles:
        print("[✓] All articles are already labeled.")
        return

    print(f"[•] Generating taxonomy for {len(raw_articles)} articles...")

    all_software = ConfigurationItem.objects.values_list("software", flat=True)
    flat_software = {item for sublist in all_software for item in sublist if isinstance(item, str)}
    hardware_vendors = ConfigurationItem.objects.values_list("hardware_vendor", flat=True).distinct()
    connectivity_types = ConfigurationItem.objects.values_list("connectivity", flat=True).distinct()
    network_zones = ConfigurationItem.objects.values_list("network_zone", flat=True).distinct()

    for article in raw_articles:
        content = article.content.lower()

        label = GeneratedTaxonomyLabel(
            raw_article=None,
            record_id=ConfigurationItem.id,
            classification_source="cmdb",
            platform=extract_keywords(content, ["windows", "linux", "macos", "android", "ios"]),
            software=extract_keywords(content, flat_software),
            connectivity=next((c for c in connectivity_types if c.lower() in content), ""),
            hardware_vendor=next((v for v in hardware_vendors if v.lower() in content), ""),
            network_zone=next((z for z in network_zones if z.lower() in content), ""),

            # Enrich from Employee or AD if match exists
            country="",
            city="",
            business_unit="",
            department="",
            security_posture="",

            severity=infer_severity(content),
            impact=infer_impact(content),
            actor=infer_actor(content),
            origin=infer_origin(content),
            compliance=infer_compliance(content)
        )

        label.save()

    print(f"[✓] Taxonomy labels created for {len(raw_articles)} articles.")


if __name__ == "__main__":
    generate_taxonomy()
