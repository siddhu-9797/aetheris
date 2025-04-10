import os
import sys

# --- Setup Django ---
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # project root
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aetheris_core.settings")

import django
django.setup()

# --- Django & ML Imports ---
from django.conf import settings
from vtagent.models import RawArticle

import faiss
import pickle
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer


def vectorize_and_store_in_faiss():
    print("[INFO] Loading raw articles from DB...")
    raw_articles = RawArticle.objects.all()

    contents = [a.content for a in raw_articles]
    ids = [a.id for a in raw_articles]

    if not contents:
        print("[WARNING] No raw articles to vectorize.")
        return

    print(f"[INFO] Vectorizing {len(contents)} articles using TF-IDF...")
    vectorizer = TfidfVectorizer(max_features=5000)
    X = vectorizer.fit_transform(contents).toarray()

    d = X.shape[1]  # vector dimensionality
    index = faiss.IndexFlatL2(d)
    index.add(np.array(X).astype(np.float32))

    # --- File Paths ---
    base_dir = settings.BASE_DIR
    index_path = os.path.join(base_dir, "aetheris_core", "faiss_index_classified_articles.index")
    metadata_path = os.path.join(base_dir, "aetheris_core", "faiss_id_map.pkl")
    vectorizer_path = os.path.join(base_dir, "aetheris_core", "faiss_vectorizer.pkl")

    # --- Save files ---
    faiss.write_index(index, index_path)

    with open(metadata_path, "wb") as f:
        pickle.dump(ids, f)

    with open(vectorizer_path, "wb") as f:
        pickle.dump(vectorizer, f)
    
    vectors_path = os.path.join(base_dir, "aetheris_core", "faiss", "article_vectors.pkl")
    os.makedirs(os.path.dirname(vectors_path), exist_ok=True)

    with open(vectors_path, "wb") as f:
        pickle.dump(X, f)

    print("[SUCCESS] Vectorization complete. Index, metadata, and vectorizer saved.")


if __name__ == "__main__":
    try:
        vectorize_and_store_in_faiss()
    except Exception as e:
        print(f"[ERROR] Vectorization failed: {e}")
