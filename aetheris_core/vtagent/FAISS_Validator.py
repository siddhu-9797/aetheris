import os
import sys

# --- Django Setup ---
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aetheris_core.settings")

import django
django.setup()

from django.conf import settings
from vtagent.models import RawArticle

import faiss
import pickle
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

# --- Load FAISS Files ---
base_dir = settings.BASE_DIR
index_path = os.path.join(base_dir, "aetheris_core", "faiss_index_classified_articles.index")
metadata_path = os.path.join(base_dir, "aetheris_core", "faiss_id_map.pkl")
vectorizer_path = os.path.join(base_dir, "aetheris_core", "faiss_vectorizer.pkl")

def validate_faiss_index():
    print("[INFO] Loading FAISS index and metadata...")
    if not os.path.exists(index_path) or not os.path.exists(metadata_path):
        print("[ERROR] FAISS index or metadata not found.")
        return

    index = faiss.read_index(index_path)

    with open(metadata_path, "rb") as f:
        id_map = pickle.load(f)

    with open(vectorizer_path, "rb") as f:
        vectorizer = pickle.load(f)

    print(f"[INFO] Loaded index with {index.ntotal} vectors.")
    
    if index.ntotal == 0:
        print("[WARNING] FAISS index is empty.")
        return

    query_article = RawArticle.objects.filter(id__in=id_map).first()
    if not query_article:
        print("[ERROR] No matching article in DB.")
        return

    print(f"[INFO] Using article ID {query_article.id} for test search.")

    query_vec = vectorizer.transform([query_article.content]).toarray().astype(np.float32)

    D, I = index.search(query_vec, k=5)

    print("\nTop 5 most similar articles:")
    for i, idx in enumerate(I[0]):
        article_id = id_map[idx]
        article = RawArticle.objects.filter(id=article_id).first()
        if article:
            print(f"  {i+1}. {article.title} (ID: {article.id})")
        else:
            print(f"  {i+1}. Article with ID {article_id} not found.")

if __name__ == "__main__":
    validate_faiss_index()
