# synthetic_data/generators/generate_firewall_logs.py

import os
import sys
import django
import random
import json
from datetime import datetime
from django.utils.timezone import now

# --- Django Setup ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aetheris_core.settings")
django.setup()

from syntheticcmdb.models import ConfigurationItem
from syntheticemployees.models import Employee

# === Predefined Values ===

PROTOCOLS = ["TCP", "UDP", "ICMP"]
ACTIONS = ["ALLOW", "BLOCK"]
INTERFACES = ["inbound", "outbound"]
FIREWALL_RULES = [
    "Allow Web Traffic",
    "Block External SSH",
    "Allow DNS",
    "Block RDP",
    "Allow Internal Email",
    "Block Suspicious IP",
]

DETECTED_THREATS = [
    None,
    "Port Scanning",
    "Malware Callback",
    "C2 Traffic",
    "Brute Force Attempt",
    None,
    None
]

def generate_firewall_logs(n_logs=300):
    logs = []
    assets = list(ConfigurationItem.objects.exclude(ip_address__isnull=True))
    
    if len(assets) < 2:
        print("[!] Not enough assets with IPs to generate firewall logs.")
        return

    for _ in range(n_logs):
        src = random.choice(assets)
        dst = random.choice([a for a in assets if a != src])

        employee = Employee.objects.filter(employee_id=src.employee_id).first()

        log = {
            "timestamp": now().isoformat(),
            "src_ip": src.ip_address,
            "dst_ip": dst.ip_address,
            "src_hostname": src.hostname,
            "dst_hostname": dst.hostname,
            "protocol": random.choice(PROTOCOLS),
            "src_port": random.randint(1024, 65535),
            "dst_port": random.randint(1, 1024),
            "interface": random.choice(INTERFACES),
            "action": random.choice(ACTIONS),
            "rule": random.choice(FIREWALL_RULES),
            "threat_detected": random.choice(DETECTED_THREATS),
            "department": src.department,
            "country": employee.country if employee else "Unknown",
            "owner": src.owner,
            "asset_type": src.asset_type,
        }

        logs.append(log)

    output_path = os.path.join("synthetic_data", "firewall_logs.json")
    with open(output_path, "w") as f:
        json.dump(logs, f, indent=2)

    print(f"[✓] Wrote {len(logs)} firewall logs to {output_path}")


if __name__ == "__main__":
    generate_firewall_logs()
