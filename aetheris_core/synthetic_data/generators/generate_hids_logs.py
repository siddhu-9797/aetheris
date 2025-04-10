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

# === HIDS Event Templates ===
HIDS_EVENTS = [
    {
        "event_type": "file_integrity_violation",
        "file_path": "/etc/passwd",
        "hash_before": fake.sha256(),
        "hash_after": fake.sha256(),
        "detection_tool": "OSSEC",
        "alert_level": "high"
    },
    {
        "event_type": "suspicious_process_tree",
        "parent_process": "explorer.exe",
        "child_process": "cmd.exe /c evil.bat",
        "detection_tool": "Wazuh",
        "alert_level": "critical"
    },
    {
        "event_type": "audit_log_tampering",
        "file_path": "/var/log/auth.log",
        "attempted_action": "deletion",
        "detection_tool": "Tripwire",
        "alert_level": "medium"
    },
    {
        "event_type": "unexpected_kernel_module",
        "module_name": "rootkit_xyz",
        "detection_tool": "Chkrootkit",
        "alert_level": "high"
    },
    {
        "event_type": "policy_violation",
        "policy": "No shell access for service accounts",
        "violating_user": "svc-backup",
        "detection_tool": "Auditd",
        "alert_level": "low"
    }
]

# === Log Generator ===
def generate_hids_logs(n=300):
    logs = []
    ci_assets = list(ConfigurationItem.objects.filter(asset_type__in=["Server", "Workstation"]))
    ad_users = list(ADUser.objects.all())

    for _ in range(n):
        asset = random.choice(ci_assets)
        user = random.choice(ad_users)
        template = random.choice(HIDS_EVENTS)

        log = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "hostname": asset.hostname,
            "ip_address": asset.ip_address,
            "username": user.display_name,
            "email": user.mail,
            "location": asset.city,
            "country": asset.country,
            "department": asset.department,
            "asset_type": asset.asset_type,
            "event_type": template["event_type"],
            "details": {k: v for k, v in template.items() if k != "event_type"}
        }
        logs.append(log)

    output_path = os.path.join("synthetic_data", "hids_logs.json")
    with open(output_path, "w") as f:
        json.dump(logs, f, indent=2)
    print(f"[✓] Wrote {len(logs)} HIDS logs to {output_path}")

if __name__ == "__main__":
    generate_hids_logs()
