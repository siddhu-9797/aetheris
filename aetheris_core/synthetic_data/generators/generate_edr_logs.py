import os
import sys
import django
import json
import random
from faker import Faker
from datetime import datetime, timedelta
import pytz

# --- Django Setup ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aetheris_core.settings")
django.setup()

from syntheticcmdb.models import ConfigurationItem
from syntheticemployees.models import Employee
from syntheticad.models import ADUser

fake = Faker()
random.seed(42)

# EDR event types and behavior profiles
BEHAVIOR_TYPES = [
    "Credential Dumping",
    "Unusual File Access",
    "Persistence Mechanism",
    "Privilege Escalation",
    "Lateral Movement",
    "Command and Control Communication",
]

TOOLS = [
    {"name": "CrowdStrike Falcon", "version": "6.50"},
    {"name": "SentinelOne", "version": "23.3"},
    {"name": "Microsoft Defender for Endpoint", "version": "Latest"},
]

PROCESS_LIST = [
    ("lsass.exe", "svchost.exe"),
    ("powershell.exe", "explorer.exe"),
    ("mimikatz.exe", "cmd.exe"),
    ("rundll32.exe", "services.exe"),
    ("wmic.exe", "winlogon.exe"),
]

REGISTRY_KEYS = [
    r"HKEY_LOCAL_MACHINE\Software\Microsoft\Windows\CurrentVersion\Run",
    r"HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services",
    r"HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run",
]

def generate_edr_logs(num_logs=300):
    logs = []
    timezone = pytz.UTC

    employees = list(Employee.objects.all())
    assets = list(ConfigurationItem.objects.filter(asset_type__icontains="Workstation"))

    if not employees or not assets:
        print("[!] No employees or assets found for generating EDR logs.")
        return

    for _ in range(num_logs):
        emp = random.choice(employees)
        asset = random.choice(assets)
        tool = random.choice(TOOLS)
        process, parent = random.choice(PROCESS_LIST)
        behavior = random.choice(BEHAVIOR_TYPES)

        log = {
            "timestamp": timezone.localize(datetime.utcnow() - timedelta(minutes=random.randint(0, 10000))).isoformat(),
            "hostname": asset.hostname,
            "ip_address": asset.ip_address or fake.ipv4_private(),
            "username": emp.name,
            "email": emp.email,
            "process_name": process,
            "parent_process": parent,
            "file_accessed": fake.file_path(depth=3),
            "registry_modified": random.choice(REGISTRY_KEYS),
            "behavior_type": behavior,
            "tool_used": f"{tool['name']} v{tool['version']}",
            "severity": random.choice(["Low", "Medium", "High", "Critical"]),
            "description": f"{process} exhibited behavior classified as {behavior} on {asset.hostname}"
        }
        logs.append(log)

    os.makedirs("synthetic_data", exist_ok=True)
    with open("synthetic_data/edr_logs.json", "w") as f:
        json.dump(logs, f, indent=2)
    print(f"[✓] Wrote {len(logs)} EDR logs to synthetic_data/edr_logs.json")

if __name__ == "__main__":
    generate_edr_logs()
