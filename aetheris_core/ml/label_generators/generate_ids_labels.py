import os
import sys
import json
import django

# --- Django Setup ---
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aetheris_core.settings")
django.setup()

from vtagent.models import GeneratedTaxonomyLabel

# --- Constants ---
LOG_TYPE = "IDS_LOGS"
JSON_PATH = os.path.join("synthetic_data", "ids_logs.json")
CLASSIFICATION_SOURCE = "ids"

# --- Load JSON Logs ---
with open(JSON_PATH, "r", encoding="utf-8") as f:
    logs = json.load(f)

# --- Delete Old Labels ---
deleted, _ = GeneratedTaxonomyLabel.objects.filter(classification_source=CLASSIFICATION_SOURCE).delete()
print(f"[✓] Deleted {deleted} old IDS labels")

# --- Create Labels ---
created = 0
for i, log in enumerate(logs[:50]):  # limit to 50
    try:
        label = GeneratedTaxonomyLabel(
            record_id=f"{LOG_TYPE}:{i}",
            classification_source=CLASSIFICATION_SOURCE,
            severity=[log.get("severity", "low")],
            impact=[log.get("impact", "unknown")],
            actor=[log.get("actor", "unknown")],
            origin=[log.get("origin", "external")],
            compliance=[log.get("compliance", "none")]
        )
        label.save()
        created += 1
    except Exception as e:
        print(f"[!] Failed to create label for log {i}: {str(e)}")

print(f"[✓] Created {created} IDS classification labels")
