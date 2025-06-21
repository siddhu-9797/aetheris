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
VECTORIZER_PATH = os.path.join("faiss", "articles", "vectorizer.pkl")

print("=== TESTING WEBDAV ARTICLE FINDABILITY ===")

# Load FAISS index and associated mappings
faiss_index = faiss.read_index(INDEX_PATH)
with open(ID_MAP_PATH, "rb") as f:
    id_map = pickle.load(f)
with open(VECTORIZER_PATH, "rb") as f:
    vectorizer = pickle.load(f)

# Find WEBDAV articles in database
webdav_articles = RawArticle.objects.filter(content__icontains='webdav')
print(f"WEBDAV articles in database: {webdav_articles.count()}")

for article in webdav_articles:
    print(f"\nArticle: {article.title}")
    print(f"ID: {article.id}")
    print(f"Published: {article.published}")
    
    # Check if this article ID is in our FAISS id_map
    try:
        faiss_position = next(i for i, mapped_id in enumerate(id_map) if mapped_id == article.id)
        print(f"✓ Found in FAISS at position {faiss_position}")
    except StopIteration:
        print(f"❌ NOT FOUND in FAISS id_map")
        continue
    
    # Test searches that should find this article
    test_queries = [
        "Microsoft WEBDAV zero-day vulnerability",
        "WEBDAV vulnerability Microsoft",
        "Microsoft patches WEBDAV",
        "WEBDAV zero day",
        article.title[:50]  # First part of the actual title
    ]
    
    print(f"\nTesting searches for this article:")
    for query in test_queries:
        query_vec = vectorizer.transform([query]).astype(np.float32).toarray()
        scores, indices = faiss_index.search(query_vec, 10)
        
        # Check if our article appears in top results
        found_position = None
        for i, idx in enumerate(indices[0]):
            if idx < len(id_map) and id_map[idx] == article.id:
                found_position = i + 1
                break
        
        if found_position:
            print(f"  '{query}' -> Found at position {found_position} (score: {scores[0][found_position-1]:.4f})")
        else:
            print(f"  '{query}' -> NOT FOUND in top 10 results")
            # Show what was found instead
            top_results = []
            for i in range(min(3, len(indices[0]))):
                if indices[0][i] < len(id_map):
                    result_id = id_map[indices[0][i]]
                    result_article = RawArticle.objects.filter(id=result_id).first()
                    if result_article:
                        top_results.append(f"{i+1}. {result_article.title[:50]}...")
            print(f"    Top results were: {'; '.join(top_results)}")

print(f"\n=== SUMMARY ===")
if webdav_articles.count() == 0:
    print("❌ No WEBDAV articles found in database!")
else:
    print(f"✓ {webdav_articles.count()} WEBDAV articles exist in database")
    print("Issue: Vector search is not ranking them highly enough for retrieval")