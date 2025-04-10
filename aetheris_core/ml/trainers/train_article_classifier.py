# ml/trainers/train_article_classifier.py

import os
import sys
import django
import joblib
import faiss
from sklearn.ensemble import RandomForestClassifier
from sklearn.multioutput import MultiOutputClassifier
from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
import pickle

# --- Django Setup ---
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aetheris_core.settings")
django.setup()

from vtagent.models import GeneratedTaxonomyLabel

# --- Paths ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FAISS_DIR = os.path.join(PROJECT_ROOT, "faiss", "articles")
MODEL_DIR = os.path.join(PROJECT_ROOT, "ml", "models")
os.makedirs(MODEL_DIR, exist_ok=True)

INDEX_PATH = os.path.join(FAISS_DIR, "index.index")
ID_MAP_PATH = os.path.join(FAISS_DIR, "id_map.pkl")
TEXTS_PATH = os.path.join(FAISS_DIR, "texts.pkl")
VECTORIZER_PATH = os.path.join(FAISS_DIR, "vectorizer.pkl")

print(f"[DEBUG] INDEX_PATH: {INDEX_PATH}")
print(f"[DEBUG] Exists? {os.path.exists(INDEX_PATH)}")

# --- Load Vectorizer & Texts ---
with open(ID_MAP_PATH, "rb") as f:
    id_map = joblib.load(f)

with open(TEXTS_PATH, "rb") as f:
    all_texts = joblib.load(f)

with open(VECTORIZER_PATH, "rb") as f:
    vectorizer = joblib.load(f)

print(f"[DEBUG] id_map sample values: {list(id_map)[:5]}")
print(f"[DEBUG] id_map type: {type(id_map)}")
print(f"[DEBUG] Total index length: {len(id_map)}")

# --- Load Labels ---
labels = GeneratedTaxonomyLabel.objects.filter(classification_source="article")
print(f"[DEBUG] Loaded {len(labels)} Article labels")

# --- Match article labels to vectorized article index ---
valid_labels = []
if isinstance(id_map, list):
    id_to_index = {rid: idx for idx, rid in enumerate(id_map)}  # build mapping for fast lookup
    print(f"[DEBUG] id_to_index sample: {list(id_to_index.items())[:5]}")
    
    for label in labels:
        try:
            if label.record_id is None:
                continue

            record_id_int = int(label.record_id)
            if record_id_int in id_to_index:
                valid_labels.append((label, id_to_index[record_id_int]))
            else:
                print(f"[!] Skipping label: record_id {record_id_int} not in id_map")
        except Exception as e:
            print(f"[!] Skipping label due to casting error: {e}")


print(f"[DEBUG] Valid labels after filtering: {len(valid_labels)}")


# --- Load all text descriptions ---
with open(TEXTS_PATH, "rb") as f:
    all_texts = pickle.load(f)

# --- Prepare Training Data ---
X_raw = []
Y = []

for label, index in valid_labels:
    try:
        X_raw.append(all_texts[index])
        Y.append([
            ";".join(label.severity),
            ";".join(label.impact),
            ";".join(label.actor),
            ";".join(label.origin),
            ";".join(label.compliance),
        ])
    except Exception as e:
        print(f"[!] Skipped label due to error: {e}")


print(f"[DEBUG] Prepared {len(X_raw)} X/y training pairs")


# --- Vectorize Text ---
X = vectorizer.transform(X_raw)
mlb = MultiLabelBinarizer()
Y_bin = mlb.fit_transform([tuple(y) for y in Y])

print(f"[DEBUG] X shape: {X.shape}, Y shape: {Y_bin.shape}")

# --- Train Model ---
model = make_pipeline(
    StandardScaler(with_mean=False),  # with_mean=False for sparse matrices
    MultiOutputClassifier(RandomForestClassifier(n_estimators=100, random_state=42))
)
model.fit(X, Y_bin)

# --- Save Model ---
model_path = os.path.join(MODEL_DIR, "article_rf.pkl")
joblib.dump(model, model_path)
print(f"[✓] Trained Article classifier saved to: {model_path}")

mlb_path = os.path.join(MODEL_DIR, "article_mlb.pkl")
joblib.dump(mlb, mlb_path)
print(f"[✓] MultiLabelBinarizer saved to: {mlb_path}")
