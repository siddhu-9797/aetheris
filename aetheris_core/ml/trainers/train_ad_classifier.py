import os
import sys
import django
import joblib
import faiss
import pickle
import numpy as np
from sklearn.multioutput import MultiOutputClassifier
from sklearn.ensemble import RandomForestClassifier


# --- Django Setup ---
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aetheris_core.settings")
django.setup()

from vtagent.models import GeneratedTaxonomyLabel

# --- FAISS + Label Paths ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))  # C:\Projects\Aetheris_POC\aetheris_core
FAISS_DIR = os.path.join(PROJECT_ROOT, "faiss", "ad")
MODEL_DIR = os.path.join(PROJECT_ROOT, "ml", "models")
os.makedirs(MODEL_DIR, exist_ok=True)

INDEX_PATH = os.path.join(FAISS_DIR, "index.index")
ID_MAP_PATH = os.path.join(FAISS_DIR, "id_map.pkl")
TEXTS_PATH = os.path.join(FAISS_DIR, "texts.pkl")
MODEL_PATH = os.path.join(MODEL_DIR, "ad_rf.pkl")

print(f"[DEBUG] INDEX_PATH: {INDEX_PATH}")
print(f"[DEBUG] Exists? {os.path.exists(INDEX_PATH)}")

# --- Load FAISS Index & Metadata ---
index = faiss.read_index(INDEX_PATH)

with open(ID_MAP_PATH, "rb") as f:
    id_map_raw = pickle.load(f)

# Convert to dict if needed
id_map = (
    {rid: idx for idx, rid in enumerate(id_map_raw)}
    if isinstance(id_map_raw, list)
    else id_map_raw
)

print(f"[DEBUG] id_map sample values: {list(id_map.items())[:5]}")
print(f"[DEBUG] id_map type: {type(id_map)}")
print(f"[DEBUG] Total index length: {index.ntotal}")

with open(TEXTS_PATH, "rb") as f:
    all_texts = pickle.load(f)

# --- Load Labels ---
labels = GeneratedTaxonomyLabel.objects.filter(classification_source="ad")
print(f"[DEBUG] Loaded {labels.count()} AD labels")

# Replace the filtering line with this:
valid_labels = []
for label in labels:
    if not label.record_id:
        continue

    if label.record_id in id_map:
        valid_labels.append((label, label.record_id))


print(f"[DEBUG] Valid labels after filtering: {len(valid_labels)}")

if not valid_labels:
    print("[ERROR] No valid training labels found.")
    sys.exit(1)

# --- Prepare X and Y ---
# Inputs (text)
X_raw = [all_texts[id_map[full_key]] for _, full_key in valid_labels]

# Labels (multi-output)
Y = [
    [
        ";".join(label.severity),
        ";".join(label.impact),
        ";".join(label.actor),
        ";".join(label.origin),
        ";".join(label.compliance),
    ]
    for label, _ in valid_labels
]


print(f"[DEBUG] Prepared {len(X_raw)} X/y training pairs")

# --- Vectorize Text Again ---
from sklearn.feature_extraction.text import TfidfVectorizer

vectorizer = TfidfVectorizer(max_features=2048)
X = vectorizer.fit_transform(X_raw)

print(f"[DEBUG] X shape: {X.shape}, Y shape: {np.array(Y).shape}")

# --- Train Model ---
model = MultiOutputClassifier(RandomForestClassifier())
model.fit(X, Y)

# --- Save Model ---
joblib.dump(model, MODEL_PATH)
print(f"[✓] Trained AD classifier saved to: {MODEL_PATH}")
