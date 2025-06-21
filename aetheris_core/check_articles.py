#!/usr/bin/env python3
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aetheris_core.settings')
django.setup()

from vtagent.models import RawArticle
from datetime import datetime, timedelta

print("=== CHECKING CURRENT THREAT ARTICLES ===")

# Check recent articles
recent_articles = RawArticle.objects.filter(scraped_at__gte=datetime.now()-timedelta(days=1))
print(f"Recent articles (last 24 hours): {recent_articles.count()}")

print("\n=== RECENT ARTICLE TITLES ===")
for i, article in enumerate(recent_articles[:10]):
    print(f"{i+1}. {article.title}")
    # Check for specific keywords
    keywords_found = []
    content_lower = article.content.lower()
    if 'webdav' in content_lower:
        keywords_found.append('WEBDAV')
    if 'microsoft' in content_lower:
        keywords_found.append('Microsoft')
    if 'zero-day' in content_lower:
        keywords_found.append('Zero-Day')
    if 'cve-2025' in content_lower:
        keywords_found.append('CVE-2025')
    
    if keywords_found:
        print(f"   -> Contains: {', '.join(keywords_found)}")

# Search for any articles containing webdav
print(f"\n=== SEARCHING FOR WEBDAV ARTICLES ===")
webdav_articles = RawArticle.objects.filter(content__icontains='webdav')
print(f"Articles containing 'webdav': {webdav_articles.count()}")

for article in webdav_articles[:3]:
    print(f"- {article.title}")
    print(f"  Published: {article.published}")
    print(f"  Source: {article.source.name}")

# Search for Microsoft articles
print(f"\n=== SEARCHING FOR MICROSOFT ARTICLES ===")
microsoft_articles = RawArticle.objects.filter(content__icontains='microsoft')
print(f"Articles containing 'microsoft': {microsoft_articles.count()}")

for article in microsoft_articles[:5]:
    print(f"- {article.title}")
    if 'zero-day' in article.content.lower():
        print("  ** Contains Zero-Day **")