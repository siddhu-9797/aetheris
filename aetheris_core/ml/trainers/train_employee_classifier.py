import os
import sys
import pickle
import time
import django
import numpy as np
from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.multiclass import OneVsRestClassifier
from sklearn.svm import LinearSVC
from sklearn.multioutput import MultiOutputClassifier
from django.conf import settings

# Django setup
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aetheris_core.settings")
django.setup()

from vtagent.models import GeneratedTaxonomyLabel
import faiss

# Inline FAISS loader
def load_vector_index(index_path, id_map_path):
    index = faiss.read_index(index_path)
    with open(id_map_path, "rb") as f:
        id_map = pickle.load(f)
    vectors = []
    for i in range(index.ntotal):
        vec = index.reconstruct(i)
        vectors.append(vec)
    return vectors, id_map

# File paths
VECTOR_FILE = os.path.join(settings.BASE_DIR, "aetheris_core", "faiss", "employees", "index.index")
ID_MAP_FILE = os.path.join(settings.BASE_DIR, "aetheris_core", "faiss", "employees", "id_map.pkl")
MODEL_OUT = os.path.join(settings.BASE_DIR, "aetheris_core", "ml", "models", "employee_rf.pkl")


# Dynamic target fields
EXCLUDE_FIELDS = {
    "id", "raw_article", "record_id", "cmdb_item", "ad_user", "employee",
    "labels_generated_at", "classification_source", "data_source", "data_origin"
}
TARGET_FIELDS = [
    f.name for f in GeneratedTaxonomyLabel._meta.get_fields()
    if f.name not in EXCLUDE_FIELDS and not f.many_to_one
]

def main():
    print("[*] Loading FAISS index and ID map...")
    vectors, id_map = load_vector_index(VECTOR_FILE, ID_MAP_FILE)
    X = []
    Y = []

    print("[*] Matching vectors to labels...")
    for i, emp_id in enumerate(id_map):
        record_id = f"Employee:{emp_id}"
        label = GeneratedTaxonomyLabel.objects.filter(
            record_id=record_id,
            data_source="Employee",
            data_origin="FAISS",
            classification_source="ML-RF"
        ).first()

        if label:
            X.append(vectors[i])
            y_row = []
            for field in TARGET_FIELDS:
                val = getattr(label, field, None)
                if isinstance(val, list):
                    y_row.append(tuple(val))
                elif val:
                    y_row.append((val,))
                else:
                    y_row.append(())
            Y.append(y_row)

    if not X or not Y:
        print("[!] No training data found.")
        return

    print(f"[✓] Loaded {len(X)} training examples.")
    print(f"[🧠] Found {len(TARGET_FIELDS)} target fields.")

    # Binarize
    mlb_list = []
    Y_bin = []

    print("[*] Binarizing labels...")
    for col in zip(*Y):
        mlb = MultiLabelBinarizer()
        Y_bin.append(mlb.fit_transform([set(x) for x in col]))
        mlb_list.append(mlb)

    Y_stacked = np.hstack(Y_bin)

    # Train
    print("[🚀] Training OneVsRest + LinearSVC multi-label classifier...")
    start = time.time()
    clf = MultiOutputClassifier(OneVsRestClassifier(LinearSVC(max_iter=2000)))
    clf.fit(X, Y_stacked)
    duration = time.time() - start

    # Save model
    print(f"[💾] Saving model to {MODEL_OUT}...")
    with open(MODEL_OUT, "wb") as f:
        pickle.dump({
            "model": clf,
            "mlb_list": mlb_list,
            "target_fields": TARGET_FIELDS,
            "id_map": id_map
        }, f)

    print(f"[✅] Training complete in {duration:.2f} seconds.")

if __name__ == "__main__":
    main()
