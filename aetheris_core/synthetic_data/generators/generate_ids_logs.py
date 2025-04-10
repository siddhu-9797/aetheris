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
from syntheticemployees.models import Employee

fake = Faker()

# IDS/IPS Attack Types
IDS_ATTACKS = [
    {
        "type": "SQL Injection",
        "signature_id": "IDS-1001",
        "description": "SQL injection attempt detected in HTTP request",
        "severity": "High",
        "protocol": "HTTP"
    },
    {
        "type": "Cross-Site Scripting (XSS)",
        "signature_id": "IDS-1002",
        "description": "XSS attack pattern detected",
        "severity": "Medium",
        "protocol": "HTTP"
    },
    {
        "type": "Remote Code Execution",
        "signature_id": "IDS-1003",
        "description": "Attempted RCE via crafted input",
        "severity": "Critical",
        "protocol": "HTTP"
    },
    {
        "type": "Port Scan",
        "signature_id": "IDS-1004",
        "description": "Multiple port probes from single source IP",
        "severity": "Low",
        "protocol": "TCP"
    },
    {
        "type": "Buffer Overflow",
        "signature_id": "IDS-1005",
        "description": "Buffer overflow pattern detected in request payload",
        "severity": "High",
        "protocol": "UDP"
    },
    {
        "type": "Command Injection",
        "signature_id": "IDS-1006",
        "description": "Detected OS command injection attempt",
        "severity": "Critical",
        "protocol": "HTTP"
    }
]

def generate_ids_logs(n=300):
    logs = []

    ad_users = list(ADUser.objects.all())
    assets = list(ConfigurationItem.objects.all())

    if not ad_users or not assets:
        print("[!] Missing ADUser or CMDB assets.")
        return []

    for _ in range(n):
        attack = random.choice(IDS_ATTACKS)
        user = random.choice(ad_users)
        employee = user.employee if hasattr(user, "employee") else None
        asset = random.choice(assets)

        log = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "detected_signature": attack["signature_id"],
            "attack_type": attack["type"],
            "severity": attack["severity"],
            "description": attack["description"],
            "protocol": attack["protocol"],
            "src_ip": fake.ipv4_public(),
            "dest_ip": asset.ip_address or fake.ipv4_private(),
            "hostname": asset.hostname,
            "asset_type": asset.asset_type,
            "detected_by": random.choice(["Snort", "Suricata"]),
            "username": user.display_name,
            "email": user.mail,
            "department": user.department,
            "country": user.country,
            "city": asset.city
        }

        logs.append(log)

    return logs

# Save logs
log_data = generate_ids_logs()
output_path = os.path.join("synthetic_data", "ids_logs.json")
with open(output_path, "w") as f:
    json.dump(log_data, f, indent=2)

print(f"[✓] Wrote {len(log_data)} IDS logs to {output_path}")
