#!/usr/bin/env python3
"""
Comprehensive trace of the WEBDAV pipeline to see where it fails
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aetheris_core.settings')
django.setup()

from llmintegration.contextual_query_pipeline import build_gemini_prompt_and_response
from vtagent.models import RawArticle
import faiss
import pickle
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

print("🔍 COMPREHENSIVE WEBDAV PIPELINE TRACE")
print("=" * 50)

# Test the exact query
test_query = "Tell me about Microsoft WEBDAV zero-day vulnerability"
print(f"Test Query: {test_query}")

# Step 1: Check if WEBDAV articles exist
webdav_articles = RawArticle.objects.filter(content__icontains='webdav')
print(f"\n1. Database Check:")
print(f"   WEBDAV articles in database: {webdav_articles.count()}")
for article in webdav_articles:
    print(f"   - {article.title}")

# Step 2: Check FAISS index
INDEX_PATH = os.path.join("faiss", "articles", "index.index")
ID_MAP_PATH = os.path.join("faiss", "articles", "id_map.pkl")
VECTORIZER_PATH = os.path.join("faiss", "articles", "vectorizer.pkl")

faiss_index = faiss.read_index(INDEX_PATH)
with open(ID_MAP_PATH, "rb") as f:
    id_map = pickle.load(f)
with open(VECTORIZER_PATH, "rb") as f:
    vectorizer = pickle.load(f)

print(f"\n2. FAISS Vector Search:")
query_vec = vectorizer.transform([test_query]).astype(np.float32).toarray()
scores, indices = faiss_index.search(query_vec, 10)
matched_ids = [id_map[i] for i in indices[0] if i < len(id_map)]

print(f"   Vector search found {len(matched_ids)} articles")
articles_from_search = RawArticle.objects.filter(id__in=matched_ids)
webdav_in_search = [a for a in articles_from_search if 'webdav' in a.content.lower()]
print(f"   WEBDAV articles in search results: {len(webdav_in_search)}")
for article in webdav_in_search:
    position = next((i+1 for i, aid in enumerate(matched_ids) if aid == article.id), "Not found")
    print(f"   - Position {position}: {article.title}")

# Step 3: Simulate the contextual query pipeline manually
print(f"\n3. Pipeline Simulation:")

# Manually replicate the key parts of build_gemini_prompt_and_response
from llmintegration.contextual_query_pipeline import classify_prompt_type, extract_filter_entities, extract_time_filter

filters = extract_filter_entities(test_query)
time_filter = extract_time_filter(test_query)
prompt_type = classify_prompt_type(test_query)

print(f"   Prompt type: {prompt_type}")
print(f"   Filters: {filters}")
print(f"   Time filter: {time_filter}")

# Apply filters
articles = RawArticle.objects.filter(id__in=matched_ids)
print(f"   Articles before time filter: {articles.count()}")

if time_filter:
    articles = articles.filter(scraped_at__gte=time_filter)
    print(f"   Articles after time filter: {articles.count()}")

articles = articles[:5]  # Limit to top 5
print(f"   Final articles for LLM: {articles.count()}")

webdav_in_final = [a for a in articles if 'webdav' in a.content.lower()]
print(f"   WEBDAV articles in final set: {len(webdav_in_final)}")

# Step 4: Check what content would be sent to LLM
print(f"\n4. Content Analysis:")
if webdav_in_final:
    print(f"   ✅ WEBDAV articles WOULD be sent to LLM:")
    for article in webdav_in_final:
        print(f"      - {article.title}")
        # Check if title mentions the vulnerability
        if 'webdav' in article.title.lower():
            print(f"        ✓ WEBDAV mentioned in title")
        snippet = article.content[:200] + "..." if len(article.content) > 200 else article.content
        if 'webdav' in snippet.lower():
            print(f"        ✓ WEBDAV mentioned in content snippet")
else:
    print(f"   ❌ NO WEBDAV articles would be sent to LLM")
    print(f"   Instead, these articles would be sent:")
    for article in articles:
        print(f"      - {article.title}")

# Step 5: Test the actual pipeline
print(f"\n5. Actual Pipeline Test:")
try:
    # This will call the actual function
    response = build_gemini_prompt_and_response(test_query, None)
    
    # Check if WEBDAV is mentioned in the response
    if 'webdav' in response.lower():
        print(f"   ✅ WEBDAV mentioned in response!")
        print(f"   Response preview: {response[:200]}...")
    else:
        print(f"   ❌ WEBDAV NOT mentioned in response")
        print(f"   Response preview: {response[:200]}...")
        
        # Check what the response says about the information
        if 'no information' in response.lower() or 'cannot find' in response.lower():
            print(f"   → LLM says it has no information about WEBDAV")
        
except Exception as e:
    print(f"   ERROR in pipeline: {e}")

print(f"\n=== CONCLUSION ===")
if len(webdav_in_final) > 0:
    print("🔧 WEBDAV articles are being found and should reach the LLM")
    print("   The issue is likely in:")
    print("   - LLM not recognizing the WEBDAV content in the articles")
    print("   - Article content truncation")
    print("   - LLM instruction interpretation")
else:
    print("🚫 WEBDAV articles are being filtered out before reaching the LLM")
    print("   The issue is in the article selection/filtering logic")