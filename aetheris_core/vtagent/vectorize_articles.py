# vtagent/vectorize_articles.py

import os
import sys
import faiss
import pickle
import django
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer

# --- Django Setup ---
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aetheris_core.settings")
django.setup()

from vtagent.models import RawArticle

# --- Load Article Content ---
articles = RawArticle.objects.exclude(content__isnull=True).exclude(content__exact="").only("id", "content")

texts = []
ids = []
for article in articles:
    texts.append(article.content.strip())
    ids.append(article.id)

print(f"[✓] Loaded {len(texts)} articles")

# --- TF-IDF Vectorization ---
vectorizer = TfidfVectorizer(max_features=2048)
X = vectorizer.fit_transform(texts).toarray()

print(f"[✓] TF-IDF matrix shape: {X.shape}")

# --- FAISS Index Creation ---
dimension = X.shape[1]
index = faiss.IndexFlatL2(dimension)
index.add(X)

# --- Output Paths ---
FAISS_OUTPUT_DIR = os.path.join("faiss", "articles")
os.makedirs(FAISS_OUTPUT_DIR, exist_ok=True)
INDEX_PATH = os.path.join(FAISS_OUTPUT_DIR, "index.index")
ID_MAP_PATH = os.path.join(FAISS_OUTPUT_DIR, "id_map.pkl")
VECTORIZER_PATH = os.path.join(FAISS_OUTPUT_DIR, "vectorizer.pkl")
TEXTS_PATH = os.path.join(FAISS_OUTPUT_DIR, "texts.pkl")

# --- Save to disk ---
faiss.write_index(index, INDEX_PATH)
with open(ID_MAP_PATH, "wb") as f:
    pickle.dump(ids, f)
with open(VECTORIZER_PATH, "wb") as f:
    pickle.dump(vectorizer, f)
with open(TEXTS_PATH, "wb") as f:
    pickle.dump(texts, f)

print(f"[✓] Vectorized {len(ids)} articles")
print(f"[✓] FAISS index stored at: {INDEX_PATH}")
print(f"[✓] ID map stored at: {ID_MAP_PATH}")
print(f"[✓] Vectorizer stored at: {VECTORIZER_PATH}")
print(f"[✓] Text descriptions stored at: {TEXTS_PATH}")
