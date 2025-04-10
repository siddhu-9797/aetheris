import os
import sys
import joblib
import faiss
import pickle
import django
import numpy as np
from sklearn.preprocessing import MultiLabelBinarizer


# --- Django Setup ---
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aetheris_core.settings")
django.setup()


from vtagent.models import RawArticle, GeneratedTaxonomyLabel

# --- Paths ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FAISS_DIR = os.path.join(PROJECT_ROOT, "..", "faiss", "articles")
MODEL_PATH = os.path.join(PROJECT_ROOT, "..", "ml", "models", "article_rf.pkl")

MLB_PATH = os.path.join(PROJECT_ROOT, "..", "ml", "models", "article_mlb.pkl")
mlb = joblib.load(MLB_PATH)

# --- Load FAISS Data ---
index_path = os.path.join(FAISS_DIR, "index.index")
id_map_path = os.path.join(FAISS_DIR, "id_map.pkl")
vectorizer_path = os.path.join(FAISS_DIR, "vectorizer.pkl")
texts_path = os.path.join(FAISS_DIR, "texts.pkl")

index = faiss.read_index(index_path)
id_map = joblib.load(id_map_path)  # Should be list of article IDs
vectorizer = joblib.load(vectorizer_path)
texts = joblib.load(texts_path)

# --- Load ML Model ---
clf = joblib.load(MODEL_PATH)

# --- Clear previous ML-RF labels ---
GeneratedTaxonomyLabel.objects.filter(classification_source="ML-RF").delete()

# --- Inference ---
X = vectorizer.transform(texts)
predictions = clf.predict(X)
predictions_bin = clf.predict(X)
predicted_labels = mlb.inverse_transform(predictions_bin)

print(f"[✓] Running inference on {len(id_map)} articles")

for idx, raw_article_id in enumerate(id_map):
    raw_article = RawArticle.objects.filter(id=raw_article_id).first()
    if not raw_article:
        continue

    try:
        labels = predicted_labels[idx]  # Tuple of flattened labels

        # Heuristic mapping based on prefix keywords
        platform = [l for l in labels if l.lower() in ["windows", "linux", "macos", "ios", "android"]]  # adjust
        severity = [l for l in labels if l.lower() in ["critical", "high", "medium", "low"]]
        impact = [l for l in labels if "breach" in l or "disruption" in l]
        actor = [l for l in labels if l.lower() in ["cybercriminal", "insider", "hacktivist"]]
        origin = [l for l in labels if l.lower() in ["internal", "external"]]
        compliance = [l for l in labels if l.lower() in ["gdpr", "hipaa", "pci", "iso27001"]]

        GeneratedTaxonomyLabel.objects.create(
            raw_article=raw_article,
            platform=platform,
            severity=severity,
            impact=impact,
            actor=actor,
            origin=origin,
            compliance=compliance,
            classification_source="ML-RF"
        )

    except Exception as e:
        print(f"[!] Failed to classify article {raw_article_id}: {e}")
