# vtagent/vectorize_employees.py

import os
import django
import sys
import pickle
import faiss
from sklearn.feature_extraction.text import TfidfVectorizer

# --- Django Setup ---
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aetheris_core.settings")
django.setup()

from syntheticemployees.models import Employee

# === Output Paths ===
faiss_dir = os.path.join("faiss", "employees")
os.makedirs(faiss_dir, exist_ok=True)

index_path = os.path.join(faiss_dir, "index.index")
id_map_path = os.path.join(faiss_dir, "id_map.pkl")
vectorizer_path = os.path.join(faiss_dir, "vectorizer.pkl")

# === Text Description Construction ===
descriptions = []
id_map = []

for emp in Employee.objects.all():
    text = f"""
    Employee Name: {emp.name}
    Email: {emp.email}
    Department: {emp.department}
    Country: {emp.country}
    City: {emp.city}
    """
    descriptions.append(text.strip())
    id_map.append(emp.id)

# === TF-IDF Vectorization ===
vectorizer = TfidfVectorizer()
vectors = vectorizer.fit_transform(descriptions).toarray().astype("float32")

# === FAISS Index Creation ===
dimension = vectors.shape[1]
index = faiss.IndexFlatL2(dimension)
index.add(vectors)

# === Save Index, ID Map, and Vectorizer ===
faiss.write_index(index, index_path)
with open(id_map_path, "wb") as f:
    pickle.dump(id_map, f)
with open(vectorizer_path, "wb") as f:
    pickle.dump(vectorizer, f)

texts_path = os.path.join(faiss_dir, "texts.pkl")
with open(texts_path, "wb") as f:
    pickle.dump(descriptions, f)

print(f"[✓] Text descriptions stored at: {texts_path}")


print(f"[✓] Vectorized {len(descriptions)} employee records")
print(f"[✓] FAISS index stored at: {index_path}")
print(f"[✓] ID map stored at: {id_map_path}")
print(f"[✓] Vectorizer stored at: {vectorizer_path}")
