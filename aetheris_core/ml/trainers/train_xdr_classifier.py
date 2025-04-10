import os
import sys
import joblib
import faiss
import pickle
import django
from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.ensemble import RandomForestClassifier

# --- Django Setup ---
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aetheris_core.settings")
django.setup()

from vtagent.models import GeneratedTaxonomyLabel

# --- Paths ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FAISS_DIR = os.path.join(PROJECT_ROOT, "faiss", "logs")
MODEL_DIR = os.path.join(PROJECT_ROOT, "ml", "models")

# --- Config ---
LOG_TYPE = "xdr_logs"
INDEX_PATH = os.path.join(FAISS_DIR, f"{LOG_TYPE}.index.index")
ID_MAP_PATH = os.path.join(FAISS_DIR, f"{LOG_TYPE}.id_map.pkl")
TEXTS_PATH = os.path.join(FAISS_DIR, f"{LOG_TYPE}.texts.pkl")
VECTORIZER_PATH = os.path.join(FAISS_DIR, f"{LOG_TYPE}.vectorizer.pkl")
MODEL_OUTPUT_PATH = os.path.join(MODEL_DIR, f"{LOG_TYPE}_rf.pkl")

print(f"[DEBUG] INDEX_PATH: {INDEX_PATH}")
print(f"[DEBUG] Exists? {os.path.exists(INDEX_PATH)}")

# --- Load FAISS index, id_map, texts, vectorizer ---
index = faiss.read_index(INDEX_PATH)

with open(ID_MAP_PATH, "rb") as f:
    id_map = pickle.load(f)

with open(TEXTS_PATH, "rb") as f:
    all_texts = pickle.load(f)

with open(VECTORIZER_PATH, "rb") as f:
    vectorizer = pickle.load(f)

print(f"[DEBUG] id_map sample values: {id_map[:5]}")
print(f"[DEBUG] id_map type: {type(id_map)}")
print(f"[DEBUG] Total index length: {index.ntotal}")

# --- Load labels ---
labels = GeneratedTaxonomyLabel.objects.filter(classification_source="xdr_logs")
print(f"[DEBUG] Loaded {labels.count()} XDR labels")

# --- Prepare id->index map ---
id_to_index = {rid: idx for idx, rid in enumerate(id_map)}
print(f"[DEBUG] id_to_index sample: {list(id_to_index.items())[:5]}")

# --- Match labels to vector index ---
valid_labels = []
for label in labels:
    if label.record_id in id_to_index:
        valid_labels.append((label, id_to_index[label.record_id]))
    else:
        print(f"[!] Skipping label with record_id {label.record_id} not found in id_map")

print(f"[DEBUG] Valid labels after filtering: {len(valid_labels)}")

# --- Prepare training data ---
X_raw = [all_texts[idx] for _, idx in valid_labels]
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

# --- Vectorize features ---
X = vectorizer.transform(X_raw)
mlb = MultiLabelBinarizer()
Y = mlb.fit_transform(Y)

print(f"[DEBUG] X shape: {X.shape}, Y shape: {Y.shape}")

# --- Train classifier ---
clf = RandomForestClassifier(n_estimators=150, random_state=42)
clf.fit(X, Y)

# --- Save model ---
os.makedirs(MODEL_DIR, exist_ok=True)
joblib.dump(clf, MODEL_OUTPUT_PATH)
print(f"[✓] Trained XDR classifier saved to: {MODEL_OUTPUT_PATH}")
