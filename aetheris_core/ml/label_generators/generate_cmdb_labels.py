import os
import django
import sys

# --- Django Setup ---
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aetheris_core.settings")
django.setup()

from vtagent.models import GeneratedTaxonomyLabel
from syntheticcmdb.models import ConfigurationItem

# --- Wipe Existing CMDB Labels ---
GeneratedTaxonomyLabel.objects.filter(classification_source="cmdb").delete()
print("[✓] Deleted previous CMDB classification labels")

# --- Generate New Labels ---
new_labels = []

for ci in ConfigurationItem.objects.all()[:50]:  # Limiting to 50 for now
    label = GeneratedTaxonomyLabel(
        raw_article=None,
        record_id=ci.id,
        classification_source="cmdb",
        platform=[ci.os],
        software=ci.software,
        connectivity=ci.connectivity,
        hardware_vendor=ci.hardware_vendor,
        network_zone=ci.network_zone,
        country=ci.country,
        city=ci.city,
        business_unit=ci.business_unit,
        department=ci.department,
        security_posture=ci.security_posture,
        severity=["Low"],       # Placeholder
        impact=["Minimal"],
        actor=["Insider"],
        origin=["Internal"],
        compliance=["ISO27001"]
    )
    new_labels.append(label)

GeneratedTaxonomyLabel.objects.bulk_create(new_labels)
print(f"[✓] Created {len(new_labels)} CMDB classification labels")
