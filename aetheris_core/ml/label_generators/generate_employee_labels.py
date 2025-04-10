import os
import sys
import django
import json

# Django setup
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aetheris_core.settings")
django.setup()

from syntheticemployees.models import Employee
from syntheticad.models import ADUser
from syntheticcmdb.models import ConfigurationItem
from vtagent.models import GeneratedTaxonomyLabel

# Settings
SAVE_TO_DB = True
SAVE_TO_JSON = True
OUTPUT_PATH = "employee_labels_ml.json"
CLASSIFIER = "ML-RF"
DATA_ORIGIN = "FAISS"
DATA_SOURCE = "Employee"
MAX_EMPLOYEES = 2000

def generate_labels(employee):
    aduser = getattr(employee, "aduser", None)

    # Gather all ConfigurationItems tied to this employee
    assets = ConfigurationItem.objects.filter(
        employee_id=employee.employee_id
    ) | ConfigurationItem.objects.filter(
        employee_email=employee.email
    )

    # Collect asset-level data
    platforms = list({asset.asset_type for asset in assets if asset.asset_type})
    software = list({s for asset in assets for s in asset.software if s}) if assets else []
    software_versions = list({asset.software_version for asset in assets if asset.software_version})
    os_versions = list({asset.os_version for asset in assets if asset.os_version})
    os_names = list({asset.os for asset in assets if asset.os})
    security_tools = list({asset.security_software for asset in assets if asset.security_software})
    ips = list({asset.ip_address for asset in assets if asset.ip_address})
    network_zones = list({asset.network_zone for asset in assets if asset.network_zone})

    # Derived fields
    compliance = []
    if employee.country == "USA":
        compliance.append("HIPAA")
    if employee.country == "UK":
        compliance.append("GDPR")
    if employee.country == "Germany":
        compliance.extend(["GDPR", "SOX"])
    if not compliance:
        compliance = ["GDPR"]

    actor = ["internal"]
    origin = ["internal"]

    # Simple logic-based severity/impact (can be replaced with LLM or more ML later)
    severity = ["high"] if "admin" in employee.email.lower() else ["medium"]
    impact = ["access misuse"]
    if any("finance" in (employee.department or "").lower() for _ in range(1)):
        impact.append("data breach")
    if "admin" in employee.email.lower():
        impact.append("privilege escalation")

    return {
        "record_id": f"Employee:{employee.id}",
        "country": employee.country,
        "city": employee.city,
        "department": employee.department,
        "business_unit": employee.business_unit,
        "platform": platforms,
        "software": software,
        "software_version": ", ".join(software_versions),
        "os": ", ".join(os_names),
        "os_version": ", ".join(os_versions),
        "security_software": ", ".join(security_tools),
        "network_zone": ", ".join(network_zones),
        "ip_address": ips[0] if ips else None,
        "severity": severity,
        "impact": impact,
        "actor": actor,
        "origin": origin,
        "compliance": list(set(compliance)),
        "data_source": DATA_SOURCE,
        "data_origin": DATA_ORIGIN,
        "classification_source": CLASSIFIER
    }

def main():
    employees = Employee.objects.all().order_by("id")[:MAX_EMPLOYEES]
    output = []

    for emp in employees:
        label_data = generate_labels(emp)

        if SAVE_TO_DB:
            from django.db.models import Q

            # Check if already labeled
            if GeneratedTaxonomyLabel.objects.filter(
                Q(record_id=f"Employee:{emp.id}"),
                Q(data_origin="FAISS"),
                Q(classification_source="ML-RF")
            ).exists():
                print(f"[↪] Skipping already labeled Employee {emp.id}")
                continue

            GeneratedTaxonomyLabel.objects.create(**label_data)
            print(f"[✓] Labeled Employee {emp.id} ({label_data['record_id']})")

        output.append(label_data)

    if SAVE_TO_JSON:
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2)
        print(f"[✓] Labels written to {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
