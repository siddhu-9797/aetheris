from faker import Faker
import random
import json
from datetime import datetime, timezone
import os
import sys
import django

# --- Django Setup ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aetheris_core.settings")
django.setup()

from syntheticcmdb.models import ConfigurationItem
from syntheticad.models import ADUser

fake = Faker()

# === APPLICATION EVENT TEMPLATES ===
APPLICATION_EVENTS = [
    {
        "event_type": "login_success",
        "description": "User successfully logged in",
        "application": "Aetheris Web Portal"
    },
    {
        "event_type": "login_failure",
        "description": "Failed login attempt",
        "application": "Aetheris Web Portal"
    },
    {
        "event_type": "record_update",
        "description": "User updated a customer record",
        "application": "CRM System"
    },
    {
        "event_type": "payment_processed",
        "description": "Payment successfully processed",
        "application": "Finance Suite"
    },
    {
        "event_type": "api_access",
        "description": "API endpoint accessed",
        "application": "Internal API Gateway"
    },
    {
        "event_type": "file_uploaded",
        "description": "Document uploaded to server",
        "application": "Document Management System"
    },
    {
        "event_type": "permission_change",
        "description": "User role modified",
        "application": "Access Control Panel"
    },
    {
        "event_type": "timeout_error",
        "description": "Application request timed out",
        "application": "Salesforce"
    },
    {
        "event_type": "report_generated",
        "description": "Quarterly report created",
        "application": "Netsuite BI"
    }
]

# === GENERATE LOGS ===
def generate_application_logs(n=300):
    logs = []
    ci_assets = list(ConfigurationItem.objects.filter(asset_type__in=["Server", "Workstation"]))
    ad_users = list(ADUser.objects.all())

    for _ in range(n):
        asset = random.choice(ci_assets)
        user = random.choice(ad_users)
        event = random.choice(APPLICATION_EVENTS)

        log = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "hostname": asset.hostname,
            "ip_address": asset.ip_address,
            "username": user.display_name,
            "email": user.mail,
            "department": asset.department,
            "country": asset.country,
            "city": asset.city,
            "application": event["application"],
            "event_type": event["event_type"],
            "description": event["description"],
            "status_code": random.choice([200, 201, 400, 403, 404, 500]),
            "response_time_ms": random.randint(20, 1500)
        }
        logs.append(log)

    output_path = os.path.join("synthetic_data", "application_logs.json")
    with open(output_path, "w") as f:
        json.dump(logs, f, indent=2)
    print(f"[✓] Wrote {len(logs)} Application logs to {output_path}")

if __name__ == "__main__":
    generate_application_logs()
