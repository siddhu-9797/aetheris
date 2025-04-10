import os
import sys
import django
import random
import json
from django.utils.timezone import now

# --- Django Setup ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aetheris_core.settings")
django.setup()

from syntheticcmdb.models import ConfigurationItem
from syntheticemployees.models import Employee

# === XDR Event Templates ===
XDR_EVENTS = [
    {
        "event_type": "ProcessCreation",
        "process": "powershell.exe",
        "parent": "explorer.exe",
        "command_line": "powershell.exe -enc aGVsbG8gd29ybGQ=",
        "technique": "T1059 - Command and Scripting Interpreter"
    },
    {
        "event_type": "CredentialDump",
        "process": "mimikatz.exe",
        "parent": "cmd.exe",
        "command_line": "mimikatz.exe \"sekurlsa::logonpasswords\"",
        "technique": "T1003 - Credential Dumping"
    },
    {
        "event_type": "NetworkConnection",
        "process": "chrome.exe",
        "parent": "explorer.exe",
        "command_line": "chrome.exe http://malicious.site",
        "technique": "T1071 - Application Layer Protocol"
    },
    {
        "event_type": "LateralMovement",
        "process": "wmic.exe",
        "parent": "cmd.exe",
        "command_line": "wmic /node:192.168.1.50 process call create 'cmd.exe /c evil.ps1'",
        "technique": "T1021 - Remote Services"
    },
]

XDR_TOOLS = [
    {"name": "CrowdStrike Falcon", "version": "6.50"},
    {"name": "SentinelOne", "version": "23.3"},
    {"name": "Microsoft Defender for Endpoint", "version": "latest"}
]

PROTOCOLS = ["TCP", "UDP", "ICMP"]
PORTS = [22, 80, 443, 445, 3389]

# === Generator Function ===
def generate_xdr_logs(n_logs=300):
    logs = []
    assets = list(ConfigurationItem.objects.exclude(ip_address__isnull=True))

    if not assets:
        print("[!] No CMDB assets with IPs available.")
        return

    for _ in range(n_logs):
        asset = random.choice(assets)
        employee = Employee.objects.filter(employee_id=asset.employee_id).first()
        event_template = random.choice(XDR_EVENTS)
        tool = random.choice(XDR_TOOLS)

        log = {
            "timestamp": now().isoformat(),
            "event_type": event_template["event_type"],
            "process": event_template["process"],
            "parent_process": event_template["parent"],
            "command_line": event_template["command_line"],
            "detected_technique": event_template["technique"],
            "tool_name": tool["name"],
            "tool_version": tool["version"],
            "hostname": asset.hostname,
            "ip_address": asset.ip_address,
            "protocol": random.choice(PROTOCOLS),
            "dst_port": random.choice(PORTS),
            "username": employee.name if employee else "Unknown",
            "email": employee.email if employee else "unknown@example.com",
            "country": employee.country if employee else "Unknown",
            "department": employee.department if employee else "Unknown"
        }

        logs.append(log)

    os.makedirs("synthetic_data", exist_ok=True)
    with open("synthetic_data/xdr_logs.json", "w") as f:
        json.dump(logs, f, indent=2)

    print(f"[✓] Wrote {len(logs)} XDR logs to synthetic_data/xdr_logs.json")

# === Run it
if __name__ == "__main__":
    generate_xdr_logs()
