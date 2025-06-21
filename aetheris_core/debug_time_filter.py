#!/usr/bin/env python3
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aetheris_core.settings')
django.setup()

from vtagent.models import RawArticle
from datetime import datetime, timedelta

print("=== DEBUGGING TIME FILTER IMPACT ===")

# Check WEBDAV articles and their timestamps
webdav_articles = RawArticle.objects.filter(content__icontains='webdav')
print(f"Total WEBDAV articles: {webdav_articles.count()}")

# Check time filter from last 24 hours
now = datetime.now()
time_filter_24h = now - timedelta(hours=24)
print(f"Time filter (last 24 hours): {time_filter_24h}")

for article in webdav_articles:
    print(f"\nArticle: {article.title}")
    print(f"Scraped at: {article.scraped_at}")
    print(f"Published: {article.published}")
    
    # Check if it passes the 24-hour filter
    if hasattr(article.scraped_at, 'replace'):
        # Handle timezone-aware datetime
        scraped_naive = article.scraped_at.replace(tzinfo=None) if article.scraped_at.tzinfo else article.scraped_at
        if scraped_naive >= time_filter_24h:
            print(f"✓ PASSES 24-hour filter")
        else:
            print(f"❌ FILTERED OUT by 24-hour constraint")
            print(f"   Time difference: {time_filter_24h - scraped_naive}")
    else:
        print(f"? Cannot check time filter (scraped_at format issue)")

# Test what happens with different queries that might trigger time filters
test_queries = [
    "Tell me about Microsoft WEBDAV zero-day vulnerability",
    "any threats in the last 24 hours",
    "Microsoft WEBDAV zero day"
]

print(f"\n=== TESTING TIME FILTER EXTRACTION ===")

def extract_time_filter(query):
    """Copy of the function from contextual_query_pipeline.py"""
    query = query.lower()
    now = datetime.now()
    
    if any(x in query for x in ["last 24 hours", "past 24 hours", "today"]):
        return now - timedelta(hours=24)
    elif any(x in query for x in ["last week", "past week"]):
        return now - timedelta(days=7)
    elif any(x in query for x in ["last month", "past month"]):
        return now - timedelta(days=30)
    return None

for query in test_queries:
    time_filter = extract_time_filter(query)
    print(f"Query: '{query}'")
    print(f"Time filter: {time_filter}")
    
    if time_filter:
        # Check how many WEBDAV articles would survive this filter
        surviving_articles = webdav_articles.filter(scraped_at__gte=time_filter)
        print(f"WEBDAV articles surviving filter: {surviving_articles.count()}")
    else:
        print(f"No time filter applied")
    print()

print("=== CONCLUSION ===")
if webdav_articles.filter(scraped_at__gte=time_filter_24h).count() == 0:
    print("❌ PROBLEM FOUND: All WEBDAV articles are being filtered out by time constraints!")
    print("Solution: Either adjust time filter logic or ensure WEBDAV articles have recent timestamps")
else:
    print("✓ Time filter is not the issue")