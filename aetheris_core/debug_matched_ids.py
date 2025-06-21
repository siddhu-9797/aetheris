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

faiss_index = faiss.read_index(INDEX_PATH)
with open(ID_MAP_PATH, "rb") as f:
    id_map = pickle.load(f)
with open(VECTORIZER_PATH, "rb") as f:
    vectorizer = pickle.load(f)

print("🔍 DEBUGGING MATCHED_IDS ISSUE")
print("=" * 40)

test_query = "Tell me about Microsoft WEBDAV zero-day vulnerability"
print(f"Query: {test_query}")

# Step 1: Vector search
query_vec = vectorizer.transform([test_query]).astype(np.float32).toarray()
scores, indices = faiss_index.search(query_vec, 20)

print(f"\nRaw FAISS results:")
for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
    print(f"  {i+1}. Index: {idx}, Score: {score:.4f}")

# Step 2: Convert to article IDs
matched_ids = [id_map[i] for i in indices[0] if i < len(id_map)]
print(f"\nMatched IDs from FAISS: {matched_ids}")

# Step 3: Check what articles these IDs correspond to
print(f"\nArticles from these IDs:")
for i, article_id in enumerate(matched_ids[:10]):
    try:
        article = RawArticle.objects.get(id=article_id)
        print(f"  {i+1}. ID {article_id}: {article.title}")
        if 'webdav' in article.content.lower():
            print(f"      ✓ Contains WEBDAV")
    except RawArticle.DoesNotExist:
        print(f"  {i+1}. ID {article_id}: NOT FOUND in database!")

# Step 4: Apply Django filter
articles = RawArticle.objects.filter(id__in=matched_ids)
print(f"\nDjango query result:")
print(f"  Articles returned by filter: {articles.count()}")
for article in articles[:10]:
    print(f"    - {article.title}")
    if 'webdav' in article.content.lower():
        print(f"      ✓ Contains WEBDAV")

# Step 5: Limit to top 5
top_articles = articles[:5]
print(f"\nTop 5 articles (what gets sent to LLM):")
for article in top_articles:
    print(f"  - {article.title}")
    if 'webdav' in article.content.lower():
        print(f"    ✓ Contains WEBDAV")

# Step 6: Check for WEBDAV articles specifically
webdav_ids = []
for article_id in matched_ids:
    try:
        article = RawArticle.objects.get(id=article_id)
        if 'webdav' in article.content.lower():
            webdav_ids.append(article_id)
    except RawArticle.DoesNotExist:
        pass

print(f"\nWEBDAV analysis:")
print(f"  WEBDAV article IDs in matched_ids: {webdav_ids}")
print(f"  Total matched_ids: {len(matched_ids)}")
print(f"  WEBDAV articles in top 5: {len([a for a in top_articles if 'webdav' in a.content.lower()])}")

if len(webdav_ids) > 0 and len([a for a in top_articles if 'webdav' in a.content.lower()]) == 0:
    print("\n❌ PROBLEM: WEBDAV articles are in matched_ids but not in top 5!")
    print("This suggests the Django query or ordering is incorrect.")
    
    # Check the ordering
    print("\nInvestigating ordering issue...")
    for i, matched_id in enumerate(matched_ids):
        if matched_id in webdav_ids:
            print(f"  WEBDAV article ID {matched_id} is at position {i+1} in matched_ids")
            if i >= 5:
                print(f"    → This is beyond the top 5 cutoff!")
            else:
                print(f"    → This should be included in top 5")

print(f"\n=== RECOMMENDATION ===")
if len(webdav_ids) > 0:
    print("The WEBDAV articles exist and are being found by vector search.")
    print("The issue is likely in the Django query ordering or the [:5] slice.")
    print("Solution: Preserve the FAISS ordering when querying Django.")
else:
    print("The WEBDAV articles are not being found by vector search.")
    print("Solution: Improve the vector search or add fallback mechanisms.")