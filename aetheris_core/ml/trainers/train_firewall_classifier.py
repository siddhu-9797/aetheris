import os
import sys
import pickle
import django
import joblib
import faiss
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import MultiLabelBinarizer

# --- Django Setup ---
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aetheris_core.settings")
django.setup()

from vtagent.models import GeneratedTaxonomyLabel

# --- Paths ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FAISS_DIR = os.path.join(PROJECT_ROOT, "faiss", "logs")
MODEL_DIR = os.path.join(PROJECT_ROOT, "ml", "models")
LOG_TYPE = "firewall_logs"
INDEX_PATH = os.path.join(FAISS_DIR, f"{LOG_TYPE}.index.index")
ID_MAP_PATH = os.path.join(FAISS_DIR, f"{LOG_TYPE}.id_map.pkl")
VECTORIZER_PATH = os.path.join(FAISS_DIR, f"{LOG_TYPE}.vectorizer.pkl")
TEXTS_PATH = os.path.join(FAISS_DIR, f"{LOG_TYPE}.texts.pkl")
MODEL_PATH = os.path.join(MODEL_DIR, f"{LOG_TYPE}_rf.pkl")

# --- Load FAISS Data ---
print(f"[DEBUG] INDEX_PATH: {INDEX_PATH}")
print(f"[DEBUG] Exists? {os.path.exists(INDEX_PATH)}")
index = faiss.read_index(INDEX_PATH)

with open(ID_MAP_PATH, "rb") as f:
    id_map = pickle.load(f)

with open(VECTORIZER_PATH, "rb") as f:
    vectorizer = pickle.load(f)

with open(TEXTS_PATH, "rb") as f:
    all_texts = pickle.load(f)

print(f"[DEBUG] id_map sample values: {id_map[:5]}")
print(f"[DEBUG] id_map type: {type(id_map)}")
print(f"[DEBUG] Total index length: {index.ntotal}")

id_to_index = (
    dict(id_map) if isinstance(id_map, list) and isinstance(id_map[0], tuple)
    else {rid: i for i, rid in enumerate(id_map)}
)
print(f"[DEBUG] id_to_index sample: {list(id_to_index.items())[:5]}")

# --- Load Labels ---
labels = GeneratedTaxonomyLabel.objects.filter(classification_source="firewall")
print(f"[DEBUG] Loaded {labels.count()} FIREWALL labels")

# --- Filter Valid Labels ---
valid_labels = []
for label in labels:
    if label.record_id is None:
        continue
    if label.record_id in id_to_index:
        valid_labels.append((label, label.record_id))
    else:
        print(f"[!] Skipping label with record_id {label.record_id} not found in id_map")

print(f"[DEBUG] Valid labels after filtering: {len(valid_labels)}")

# --- Prepare Training Data ---
X_raw = [all_texts[id_to_index[rid]] for _, rid in valid_labels]
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

if len(X_raw) == 0:
    print("[ERROR] No valid training data found.")
    sys.exit(1)

X = vectorizer.transform(X_raw)
mlb = MultiLabelBinarizer()
Y_multi = mlb.fit_transform([tuple(y) for y in Y])

print(f"[DEBUG] X shape: {X.shape}, Y shape: {Y_multi.shape}")

# --- Train ---
clf = RandomForestClassifier(n_estimators=100, random_state=42)
clf.fit(X, Y_multi)

# --- Save ---
os.makedirs(MODEL_DIR, exist_ok=True)
joblib.dump(clf, MODEL_PATH)
print(f"[✓] Trained FIREWALL classifier saved to: {MODEL_PATH}")
