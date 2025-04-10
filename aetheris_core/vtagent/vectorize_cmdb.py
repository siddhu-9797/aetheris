# vectorize_cmdb.py

import os
import sys
import django
import pickle
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
import faiss

# --- Django Setup ---
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aetheris_core.settings")
django.setup()

from syntheticcmdb.models import ConfigurationItem

# --- Output Paths ---
FAISS_OUTPUT_DIR = os.path.join("faiss", "cmdb")
os.makedirs(FAISS_OUTPUT_DIR, exist_ok=True)
INDEX_PATH = os.path.join(FAISS_OUTPUT_DIR, "index.index")
ID_MAP_PATH = os.path.join(FAISS_OUTPUT_DIR, "id_map.pkl")
VECTORIZER_PATH = os.path.join(FAISS_OUTPUT_DIR, "vectorizer.pkl")
TEXTS_PATH = os.path.join(FAISS_OUTPUT_DIR, "texts.pkl")  # ✅ Save descriptions

# --- Serialize CMDB record ---
def serialize_cmdb(item):
    return f"""
    Hostname: {item.hostname}
    Asset Type: {item.asset_type}
    OS: {item.os} {item.os_version}
    Software: {", ".join(item.software)}
    Software Version: {item.software_version}
    Hardware: {item.hardware_vendor} {item.model}
    Network Zone: {item.network_zone}
    Connectivity: {item.connectivity}
    Security Software: {item.security_software}
    Business Unit: {item.business_unit}
    Department: {item.department}
    Employee ID: {item.employee_id}
    Email: {item.employee_email}
    Country: {item.country}, City: {item.city}
    Owner: {item.owner}
    Security Posture: {item.security_posture}
    """

# --- Fetch and vectorize data ---
records = ConfigurationItem.objects.all()
texts = [serialize_cmdb(r) for r in records]
ids = [r.id for r in records]

vectorizer = TfidfVectorizer(max_features=2048)
vectors = vectorizer.fit_transform(texts).toarray().astype("float32")

index = faiss.IndexFlatL2(vectors.shape[1])
index.add(vectors)

# --- Save to disk ---
faiss.write_index(index, INDEX_PATH)

with open(ID_MAP_PATH, "wb") as f:
    pickle.dump(ids, f)

with open(VECTORIZER_PATH, "wb") as f:
    pickle.dump(vectorizer, f)

with open(TEXTS_PATH, "wb") as f:  # ✅ Fix: use `texts`, not `descriptions`
    pickle.dump(texts, f)

print(f"[✓] Vectorized {len(records)} CMDB records")
print(f"[✓] FAISS index stored at: {INDEX_PATH}")
print(f"[✓] ID map stored at: {ID_MAP_PATH}")
print(f"[✓] Vectorizer stored at: {VECTORIZER_PATH}")
print(f"[✓] Text descriptions stored at: {TEXTS_PATH}")
