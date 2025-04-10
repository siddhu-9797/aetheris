# predict_with_trained_models.py

import os
import django
import joblib
import numpy as np
from scipy.sparse import load_npz
from sklearn.preprocessing import MultiLabelBinarizer
from django.conf import settings
from django.utils.timezone import now
import sys

# Setup Django
#sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aetheris_core.settings")
django.setup()

from vtagent.models import RawArticle, GeneratedTaxonomyLabel

# --- Load FAISS vectorized matrix ---
print("[*] Loading vectorized articles...")
vectorized_path = os.path.join(settings.BASE_DIR, "aetheris_core", "faiss_vectorized_articles.npz")
id_map_path = os.path.join(settings.BASE_DIR, "aetheris_core", "faiss_id_map.pkl")

X = load_npz(vectorized_path)
article_ids = joblib.load(id_map_path)

# --- Load Trained Models ---
print("[*] Loading trained ML models...")
models_dir = os.path.join(settings.BASE_DIR, "aetheris_core", "models")
models = {
    "ML-XGBoost": joblib.load(os.path.join(models_dir, "ML-XGBoost_model.pkl")),
    "ML-LinearSVC": joblib.load(os.path.join(models_dir, "ML-LinearSVC_model.pkl")),
    "ML-LogisticRegression": joblib.load(os.path.join(models_dir, "ML-LogisticRegression_model.pkl")),
}


# --- Load MultiLabelBinarizer ---
with open(os.path.join(models_dir, "label_names.pkl"), "rb") as f:
    label_names = joblib.load(f)

# --- Run Predictions ---
print("[*] Running predictions for all models...")

for model_name, model in models.items():
    print(f"[+] Predicting with {model_name}...")
    predictions = model.predict(X)

    for idx, article_id in enumerate(article_ids):
        y_pred = predictions[idx]
        labels = [label_names[i] for i, val in enumerate(y_pred) if val == 1]  # Get list of labels

        # Organize by type
        taxonomy_data = {
            "platform": [], "software": [], "connectivity": "",
            "hardware_vendor": "", "network_zone": "",
            "country": "", "city": "", "business_unit": "", "department": "",
            "security_posture": "",
            "severity": [], "impact": [], "actor": [], "origin": "", "compliance": []
        }

        for label in labels:
            for key in taxonomy_data:
                if label.lower().startswith(key.lower()):
                    if isinstance(taxonomy_data[key], list):
                        taxonomy_data[key].append(label)
                    else:
                        taxonomy_data[key] = label

        # Save or update label for article + model
        GeneratedTaxonomyLabel.objects.update_or_create(
            raw_article_id=article_id,
            classification_source=model_name,
            defaults={
                **taxonomy_data,
                "labels_generated_at": now()
            }
        )

    print(f"[✓] Completed predictions with {model_name}.")

print("[✓] All predictions completed.")
