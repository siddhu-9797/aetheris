import os
import sys
import django
import random
from faker import Faker

# Django Setup
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aetheris_core.settings")
django.setup()


from vtagent.models import GeneratedTaxonomyLabel
from syntheticad.models import ADUser as TargetModel

fake = Faker()

def generate_ad_labels():
    # Clean up existing labels for this type
    deleted, _ = GeneratedTaxonomyLabel.objects.filter(classification_source="ad").delete()
    print(f"[✓] Deleted {deleted} old AD labels")

    all_users = TargetModel.objects.all()
    if not all_users:
        print("[!] No AD Users found.")
        return

    created = 0
    for user in all_users[:50]:
        try:
            label = GeneratedTaxonomyLabel(
                record_id=f"ADUser:{user.id}",
                country=user.country,
                city=fake.city(),
                business_unit=fake.bs().split()[0].capitalize(),
                department=user.department,
                security_posture=random.choice(["compliant", "non-compliant", "patch-needed"]),
                severity=[random.choice(["low", "medium", "high", "critical"])],
                impact=[random.choice(["insider threat", "account compromise"])],
                actor=[random.choice(["insider", "external", "unknown"])],
                origin=[random.choice(["internal", "external"])],
                compliance=[random.choice(["ISO27001", "SOC2", "None"])],
                classification_source="ad"
            )
            label.save()
            created += 1
        except Exception as e:
            print(f"[!] Failed to generate label for user {user.id}: {e}")

    print(f"[✓] Created {created} AD classification labels")

if __name__ == "__main__":
    generate_ad_labels()
