# faiss_query_utils.py

import os
import pickle
import faiss
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sentence_transformers import SentenceTransformer


# --- CONFIG ---
FAISS_BASE = os.path.join("faiss")

# Can switch between TF-IDF and Transformer
VECTORIZERS = {
    "articles": "articles/vectorizer.pkl",
    "siem_logs": "logs/siem.vectorizer.pkl",
    "employees": "employees/vectorizer.pkl"
}


# Load vectorizer (TF-IDF or SentenceTransformer) dynamically
def load_vectorizer(path):
    full_path = os.path.join(FAISS_BASE, path)
    with open(full_path, "rb") as f:
        return pickle.load(f)


# Load index and ID map
def load_faiss_index(index_path):
    index = faiss.read_index(os.path.join(FAISS_BASE, index_path, "index.index"))
    with open(os.path.join(FAISS_BASE, index_path, "id_map.pkl"), "rb") as f:
        id_map = pickle.load(f)
    with open(os.path.join(FAISS_BASE, index_path, "texts.pkl"), "rb") as f:
        texts = pickle.load(f)
    return index, id_map, texts


# Core function to perform similarity search
def search_similar(query_text, index_key, top_k=5, use_transformer=False):
    index_path = index_key.replace(".vectorizer.pkl", "") if index_key.endswith(".pkl") else index_key
    index, id_map, texts = load_faiss_index(index_path)

    if use_transformer:
        model = SentenceTransformer("all-MiniLM-L6-v2")
        query_vec = model.encode([query_text]).astype(np.float32)
    else:
        vectorizer_path = VECTORIZERS.get(index_path)
        if not vectorizer_path:
            raise ValueError(f"No vectorizer configured for {index_path}")
        vectorizer = load_vectorizer(vectorizer_path)
        query_vec = vectorizer.transform([query_text]).astype(np.float32).toarray()

    scores, indices = index.search(query_vec, top_k)
    matches = [(id_map[i], texts[i], float(scores[0][rank])) for rank, i in enumerate(indices[0]) if i < len(id_map)]
    return matches
