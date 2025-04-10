import os
import sys
import django
import json
import random


# --- Django Setup ---
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aetheris_core.settings")
django.setup()

# --- Paths ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SIEM_LOG_FILE = os.path.join(PROJECT_ROOT, "synthetic_data", "siem_logs.json")

from vtagent.models import GeneratedTaxonomyLabel

# --- Load Logs ---
with open(SIEM_LOG_FILE, "r") as f:
    siem_logs = json.load(f)

print(f"[DEBUG] Loaded {len(siem_logs)} SIEM logs")

# --- Label Generator ---
def generate_labels():
    old_labels = GeneratedTaxonomyLabel.objects.filter(classification_source="siem")
    count = old_labels.count()
    old_labels.delete()
    print(f"[✓] Deleted {count} old SIEM labels")

    created = 0
    for i, log in enumerate(siem_logs[:50]):
        try:
            label = GeneratedTaxonomyLabel(
                record_id=f"SIEM_LOGS:{i}",
                classification_source="siem",
                severity=[random.choice(["low", "medium", "high", "critical"])],
                impact=[random.choice(["unauthorized access", "data exfiltration", "ransomware"])],
                actor=[random.choice(["insider", "external", "unknown"])],
                origin=[random.choice(["internal", "external"])],
                compliance=[random.choice(["GDPR", "ISO27001", "HIPAA"])],
            )
            label.save()
            created += 1
        except Exception as e:
            print(f"[!] Failed to generate label for SIEM log {i}: {e}")

    print(f"[✓] Created {created} SIEM classification labels")

# --- Run ---
if __name__ == "__main__":
    generate_labels()
