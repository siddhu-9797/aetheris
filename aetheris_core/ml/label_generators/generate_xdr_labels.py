import os
import sys
import json
import django

# --- Django Setup ---
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aetheris_core.settings")
django.setup()

from vtagent.models import GeneratedTaxonomyLabel

# --- Config ---
LOG_TYPE = "XDR_LOGS"
SOURCE_FILE = os.path.join("synthetic_data", "xdr_logs.json")

# --- Delete old labels ---
deleted, _ = GeneratedTaxonomyLabel.objects.filter(classification_source="xdr_logs").delete()
print(f"[✓] Deleted {deleted} old XDR labels")

# --- Load synthetic logs ---
with open(SOURCE_FILE, "r", encoding="utf-8") as f:
    logs = json.load(f)

# --- Create labels ---
created = 0
for i, log in enumerate(logs[:50]):
    try:
        label = GeneratedTaxonomyLabel(
            record_id=f"{LOG_TYPE}:{i}",
            classification_source="xdr_logs",
            severity=log.get("severity", []),
            impact=log.get("impact", []),
            actor=log.get("actor", []),
            origin=log.get("origin", []),
            compliance=log.get("compliance", []),
        )
        label.save()
        created += 1
    except Exception as e:
        print(f"[!] Failed to generate label for log {i}: {str(e)}")

print(f"[✓] Created {created} XDR classification labels")
