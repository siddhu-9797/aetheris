import os
import json
import django
import sys
from datetime import datetime

# --- Django Setup ---
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aetheris_core.settings")
django.setup()

from vtagent.models import GeneratedTaxonomyLabel

# --- Paths ---
LOG_FILE = os.path.join("synthetic_data", "firewall_logs.json")

# --- Delete old labels ---
deleted, _ = GeneratedTaxonomyLabel.objects.filter(classification_source="firewall").delete()
print(f"[✓] Deleted {deleted} old FIREWALL labels")

# --- Load logs ---
with open(LOG_FILE, "r") as f:
    logs = json.load(f)

# --- Generate labels ---
count = 0
for i, log in enumerate(logs[:50]):
    try:
        event = log.get("event", {})
        label = GeneratedTaxonomyLabel(
            record_id=f"FIREWALL_LOGS:{i}",
            severity=[event.get("severity", "medium")],
            impact=[event.get("impact", "unknown")],
            actor=[event.get("actor", "external")],
            origin=[event.get("origin", "external")],
            compliance=[event.get("compliance", "N/A")],
            classification_source="firewall",
        )
        label.save()
        count += 1
    except Exception as e:
        print(f"[!] Failed to generate label for log {i}: {str(e)}")

print(f"[✓] Created {count} FIREWALL classification labels")
