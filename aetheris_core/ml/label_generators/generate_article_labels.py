# ml/label_generators/generate_article_labels.py

import os
import sys
import django
from faker import Faker
import random

# --- Django Setup ---
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aetheris_core.settings")
django.setup()

from vtagent.models import RawArticle, GeneratedTaxonomyLabel

# --- Constants ---
CLASSIFICATION_SOURCE = "article"
SEVERITY_OPTIONS = ["low", "medium", "high", "critical"]
IMPACT_OPTIONS = ["data breach", "service disruption", "financial loss", "reputation damage"]
ACTOR_OPTIONS = ["cybercriminal", "APT group", "insider threat", "hacktivist"]
ORIGIN_OPTIONS = ["internal", "external"]
COMPLIANCE_OPTIONS = ["GDPR", "HIPAA", "PCI-DSS", "SOX", "None"]

# --- Init ---
faker = Faker()

# --- Delete old labels ---
deleted = GeneratedTaxonomyLabel.objects.filter(classification_source=CLASSIFICATION_SOURCE).delete()
print(f"[✓] Deleted {deleted[0]} old Article labels")

# --- Create synthetic labels ---
articles = RawArticle.objects.all()[:50]  # adjust range if needed
created_count = 0

for article in articles:
    try:
        label = GeneratedTaxonomyLabel(
            raw_article=article,
            record_id=article.id,
            classification_source=CLASSIFICATION_SOURCE,
            severity=[random.choice(SEVERITY_OPTIONS)],
            impact=random.sample(IMPACT_OPTIONS, k=2),
            actor=[random.choice(ACTOR_OPTIONS)],
            origin=[random.choice(ORIGIN_OPTIONS)],
            compliance=random.sample(COMPLIANCE_OPTIONS, k=1),
        )
        label.save()
        created_count += 1
    except Exception as e:
        print(f"[!] Failed to generate label for article {article.id}: {e}")

print(f"[✓] Created {created_count} Article classification labels")
