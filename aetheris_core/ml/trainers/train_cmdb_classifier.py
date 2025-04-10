# train_cmdb_classifier.py

import os
import sys
import django
import joblib
import pickle
from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.multioutput import MultiOutputClassifier
import faiss

# --- Ensure we can import Django settings ---
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aetheris_core.settings")
django.setup()


from vtagent.models import GeneratedTaxonomyLabel

# --- Correct Path Setup ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))  # C:\Projects\Aetheris_POC\aetheris_core
FAISS_DIR = os.path.join(PROJECT_ROOT, "faiss", "cmdb")
MODEL_DIR = os.path.join(PROJECT_ROOT, "ml", "models")

INDEX_PATH = os.path.join(FAISS_DIR, "index.index")
ID_MAP_PATH = os.path.join(FAISS_DIR, "id_map.pkl")
TEXTS_PATH = os.path.join(FAISS_DIR, "texts.pkl")
VECTORIZER_PATH = os.path.join(FAISS_DIR, "vectorizer.pkl")

# Debug paths to confirm
print(f"[DEBUG] INDEX_PATH: {INDEX_PATH}")
print(f"[DEBUG] Exists? {os.path.exists(INDEX_PATH)}")


# --- Load FAISS and metadata ---
index = faiss.read_index(INDEX_PATH)

with open(ID_MAP_PATH, "rb") as f:
    id_map = pickle.load(f)  # dict: {record_id: vector_index}
# Convert list to dict for safer access
if isinstance(id_map, list):
    id_map = {rid: idx for idx, rid in enumerate(id_map)}

print(f"[DEBUG] id_map sample values: {list(id_map.items())[:5]}")

with open(VECTORIZER_PATH, "rb") as f:
    vectorizer = pickle.load(f)

with open(TEXTS_PATH, "rb") as f:
    all_texts = pickle.load(f)

print(f"[DEBUG] id_map type: {type(id_map)}")
#print(f"[DEBUG] id_map sample values: {id_map[:5]}")
print(f"[DEBUG] Total index length: {len(id_map)}")

# --- Load Labels ---
labels = GeneratedTaxonomyLabel.objects.filter(classification_source="cmdb")
print(f"[DEBUG] Loaded {labels.count()} labels")

# --- Match valid labels
valid_labels = [label for label in labels if label.record_id is not None and int(label.record_id) in id_map]
print(f"[DEBUG] Valid labels after filtering: {len(valid_labels)}")

if not valid_labels:
    print("[ERROR] No valid training labels found.")
    sys.exit(1)

# --- Prepare X and y ---
X_raw = [all_texts[id_map[int(label.record_id)]] for label in valid_labels]
y = [
    label.severity + label.impact + label.actor + label.origin + label.compliance
    for label in valid_labels
]

print(f"[DEBUG] Prepared {len(X_raw)} X/y training pairs")

# --- Vectorize X
X = vectorizer.transform(X_raw)

# --- Binarize Y (flattened)
mlb = MultiLabelBinarizer()
Y = mlb.fit_transform(y)

print(f"[DEBUG] X shape: {X.shape}, Y shape: {Y.shape}")

# --- Train Multi-Label Model
model = MultiOutputClassifier(RandomForestClassifier(n_estimators=100, random_state=42))
model.fit(X, Y)

# --- Save Model
MODEL_PATH = os.path.join(MODEL_DIR, "cmdb_rf.pkl")
joblib.dump(model, MODEL_PATH)
print(f"[✓] Trained CMDB classifier saved to: {MODEL_PATH}")
