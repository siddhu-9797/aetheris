#!/usr/bin/env python3
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aetheris_core.settings')
django.setup()

from vtagent.models import RawArticle
import faiss
import pickle
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

# Load FAISS components
INDEX_PATH = os.path.join("faiss", "articles", "index.index")
ID_MAP_PATH = os.path.join("faiss", "articles", "id_map.pkl")
TEXTS_PATH = os.path.join("faiss", "articles", "texts.pkl")
VECTORIZER_PATH = os.path.join("faiss", "articles", "vectorizer.pkl")

print("=== DEBUGGING VECTOR SEARCH FOR WEBDAV ===")

# Check if FAISS files exist
if not os.path.exists(INDEX_PATH):
    print(f"❌ FAISS index not found at {INDEX_PATH}")
    sys.exit(1)

# Load FAISS index and associated mappings
faiss_index = faiss.read_index(INDEX_PATH)
with open(ID_MAP_PATH, "rb") as f:
    id_map = pickle.load(f)
with open(TEXTS_PATH, "rb") as f:
    texts = pickle.load(f)
with open(VECTORIZER_PATH, "rb") as f:
    vectorizer = pickle.load(f)

print(f"✓ FAISS index loaded with {faiss_index.ntotal} vectors")
print(f"✓ ID map has {len(id_map)} entries")
print(f"✓ Texts has {len(texts)} entries")

# Test the exact query from our test
test_query = "Any affected assets regarding the WEBDAV Zero-Day?"
print(f"\n=== TESTING QUERY: {test_query} ===")

# Vectorize the query
query_vec = vectorizer.transform([test_query]).astype(np.float32).toarray()
print(f"Query vector shape: {query_vec.shape}")

# Search
scores, indices = faiss_index.search(query_vec, 10)
print(f"Search returned {len(indices[0])} results")

# Get matched article IDs
matched_ids = [id_map[i] for i in indices[0] if i < len(id_map)]
print(f"Matched article IDs: {matched_ids}")

# Fetch the articles
articles = RawArticle.objects.filter(id__in=matched_ids)
print(f"\n=== TOP SEARCH RESULTS ===")
for i, article in enumerate(articles[:5]):
    score = scores[0][i] if i < len(scores[0]) else 0
    print(f"{i+1}. [Score: {score:.4f}] {article.title}")
    print(f"   Source: {article.source.name}")
    print(f"   Published: {article.published}")
    
    # Check if this article contains webdav
    if 'webdav' in article.content.lower():
        print(f"   ✓ Contains WEBDAV content")
    else:
        print(f"   - No WEBDAV content")

# Now test a more direct search
print(f"\n=== TESTING DIRECT WEBDAV SEARCH ===")
webdav_query = "Microsoft WEBDAV zero day vulnerability"
query_vec2 = vectorizer.transform([webdav_query]).astype(np.float32).toarray()
scores2, indices2 = faiss_index.search(query_vec2, 10)
matched_ids2 = [id_map[i] for i in indices2[0] if i < len(id_map)]
articles2 = RawArticle.objects.filter(id__in=matched_ids2)

print(f"Direct WEBDAV search results:")
for i, article in enumerate(articles2[:5]):
    score = scores2[0][i] if i < len(scores2[0]) else 0
    print(f"{i+1}. [Score: {score:.4f}] {article.title}")
    if 'webdav' in article.content.lower():
        print(f"   ✓ Contains WEBDAV content")

# Finally, check if the WEBDAV articles are in the FAISS index at all
print(f"\n=== CHECKING IF WEBDAV ARTICLES ARE INDEXED ===")
webdav_articles = RawArticle.objects.filter(content__icontains='webdav')
for article in webdav_articles:
    if article.id in [id_map[i] for i in range(len(id_map))]:
        print(f"✓ Article '{article.title}' IS in FAISS index")
    else:
        print(f"❌ Article '{article.title}' NOT in FAISS index")
        print(f"   ID: {article.id}, Scraped: {article.scraped_at}")