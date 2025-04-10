import os
import sys
import random
import json
from django.utils import timezone
import django
from faker import Faker

# --- Django Setup ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aetheris_core.settings")
django.setup()

from syntheticemployees.models import Employee
from syntheticad.models import ADUser
from syntheticcmdb.models import ConfigurationItem

fake = Faker()

OUTPUT_FILE = "synthetic_data/siem_logs.json"
NUM_LOGS = 300

# === Expanded Event Types ===
EVENT_TYPES = {
    "Access Control": [
        {"type": "Unauthorized Access", "detail": "Failed Login", "method": ["SSH", "RDP", "Web Interface"]},
        {"type": "Unauthorized Access", "detail": "Account Lockout", "reason": ["Multiple Failed Attempts", "Policy Violation"]},
        {"type": "Privilege Escalation", "detail": "Sudo Abuse", "target": "root"},
        {"type": "Lateral Movement", "detail": "Pass-the-Hash"}
    ],
    "Malware": [
        {"type": "Malware Detected", "detail": "Ransomware", "malware_name": "WannaCry", "action": "Blocked"},
        {"type": "Malware Detected", "detail": "Trojan", "malware_name": "Emotet", "action": "Quarantined"},
        {"type": "Suspicious Process", "detail": "PowerShell Script", "process_name": "evil.ps1", "behavior": "Downloading File"}
    ],
    "Data Loss": [
        {"type": "Data Exfiltration", "detail": "Large File Transfer", "amount": "10GB", "protocol": "FTP"},
        {"type": "Data Exfiltration", "detail": "Email Attachment", "recipient": "external@example.com", "file_type": "Sensitive Doc"},
        {"type": "Data Manipulation", "detail": "Database Alteration", "table": "Customers", "query": "UPDATE"}
    ],
    "Network": [
        {"type": "Denial of Service", "detail": "SYN Flood", "source": "192.168.1.100"},
        {"type": "Port Scan", "detail": "TCP Connect Scan", "source": "10.0.0.5"},
        {"type": "Suspicious Communication", "detail": "C&C Beacon", "target": "198.51.100.1"}
    ]
}

# === Expanded Tools ===
TOOLS = {
    "SIEM": [
        {"name": "Splunk", "version": "9.0", "capabilities": ["Log Management", "Correlation", "Dashboards"]},
        {"name": "Elastic SIEM", "version": "8.5", "capabilities": ["Search", "Analytics", "Alerting"]},
        {"name": "IBM QRadar", "version": "7.4", "capabilities": ["Event Collection", "Offenses", "Forensics"]},
        {"name": "Microsoft Sentinel", "version": "Latest", "capabilities": ["Cloud-Native", "SOAR", "Threat Intelligence"]}
    ],
    "EDR": [
        {"name": "CrowdStrike Falcon", "version": "6.50", "capabilities": ["Endpoint Detection", "Response", "Threat Hunting"]},
        {"name": "SentinelOne", "version": "23.3", "capabilities": ["AI-Powered", "ActiveEDR", "Ranger IoT"]},
        {"name": "Microsoft Defender for Endpoint", "version": "Latest", "capabilities": ["Endpoint Protection", "EDR", "Vulnerability Management"]}
    ],
    "Other": [
        {"name": "Nessus", "version": "10.5", "capabilities": ["Vulnerability Scanning"]},
        {"name": "Wireshark", "version": "4.0", "capabilities": ["Packet Analysis"]}
    ]
}


def generate_siem_logs(num_logs):
    logs = []
    users = list(ADUser.objects.all())
    assets = list(ConfigurationItem.objects.all())

    for _ in range(num_logs):
        user = random.choice(users)
        employee = user.employee

        # Match asset with employee email or fallback by department
        matching_assets = [a for a in assets if a.employee_email == employee.email]
        asset = random.choice(matching_assets) if matching_assets else random.choice(assets)

        category = random.choice(list(EVENT_TYPES.keys()))
        event_detail = random.choice(EVENT_TYPES[category])

        tool_type = random.choice(list(TOOLS.keys()))
        tool = random.choice(TOOLS[tool_type])

        log = {
            "timestamp": timezone.now().isoformat(),
            "category": category,
            "event_type": event_detail.get("type"),
            "event_detail": event_detail.get("detail"),
            "tool": tool["name"],
            "tool_version": tool["version"],
            "tool_capabilities": tool["capabilities"],
            "username": user.display_name,
            "email": employee.email,
            "hostname": asset.hostname,
            "ip_address": asset.ip_address or "0.0.0.0",
            "city": asset.city,
            "country": asset.country,
            "department": asset.department,
            "asset_type": asset.asset_type,
            "severity": random.choice(["Low", "Medium", "High", "Critical"]),
            "description": f"{event_detail.get('type')} - {event_detail.get('detail')} on {asset.hostname} for user {user.display_name}"
        }

        # Merge additional metadata into description if exists
        for k, v in event_detail.items():
            if k not in ["type", "detail"]:
                log[k] = v

        logs.append(log)

    return logs


if __name__ == "__main__":
    logs = generate_siem_logs(NUM_LOGS)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(logs, f, indent=2)
    print(f"[✓] Wrote {len(logs)} SIEM logs to {OUTPUT_FILE}")
