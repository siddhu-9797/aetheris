#!/usr/bin/env python3
"""
Simple ML classifier that processes RawArticles into ClassifiedArticles
without heavy transformer models to avoid timeouts.
"""

import os
import django
import sys
from datetime import datetime

# Django setup
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aetheris_core.settings")
django.setup()

from vtagent.models import RawArticle, ClassifiedArticle

def simple_classify_article(content):
    """Simple keyword-based classification"""
    content_lower = content.lower()
    
    # Simple keyword matching
    classification = {
        'VT_PrimaryType': [],
        'VT_Subtype': [],
        'Industry': [],
        'Platform': [],
        'Severity': [],
        'Impact': [],
        'Actor': [],
        'Origin': [],
        'Compliance': []
    }
    
    # Primary type detection
    if any(word in content_lower for word in ['vulnerability', 'cve', 'exploit', 'patch']):
        classification['VT_PrimaryType'].append('vulnerability')
    if any(word in content_lower for word in ['attack', 'breach', 'incident', 'compromise']):
        classification['VT_PrimaryType'].append('cyber attack')
    if any(word in content_lower for word in ['threat', 'malware', 'ransomware']):
        classification['VT_PrimaryType'].append('threat')
    
    # Subtype detection
    if any(word in content_lower for word in ['phishing', 'email', 'spear']):
        classification['VT_Subtype'].append('phishing')
    if any(word in content_lower for word in ['malware', 'trojan', 'virus']):
        classification['VT_Subtype'].append('malware')
    if any(word in content_lower for word in ['ransomware', 'encrypt']):
        classification['VT_Subtype'].append('ransomware')
    if any(word in content_lower for word in ['ddos', 'dos', 'denial of service']):
        classification['VT_Subtype'].append('ddos')
    
    # Platform detection
    if any(word in content_lower for word in ['windows', 'microsoft']):
        classification['Platform'].append('Windows')
    if any(word in content_lower for word in ['linux', 'ubuntu', 'redhat']):
        classification['Platform'].append('Linux')
    if any(word in content_lower for word in ['macos', 'apple', 'mac']):
        classification['Platform'].append('macOS')
    if any(word in content_lower for word in ['cloud', 'aws', 'azure', 'gcp']):
        classification['Platform'].append('Cloud')
    if any(word in content_lower for word in ['android', 'ios', 'mobile']):
        classification['Platform'].append('Mobile')
    
    # Severity detection
    if any(word in content_lower for word in ['critical', 'severe', 'emergency']):
        classification['Severity'].append('critical')
    elif any(word in content_lower for word in ['high', 'serious', 'major']):
        classification['Severity'].append('high')
    elif any(word in content_lower for word in ['medium', 'moderate']):
        classification['Severity'].append('medium')
    else:
        classification['Severity'].append('low')
    
    # Impact detection
    if any(word in content_lower for word in ['data breach', 'stolen', 'leaked']):
        classification['Impact'].append('data breach')
    if any(word in content_lower for word in ['financial', 'money', 'payment']):
        classification['Impact'].append('financial loss')
    if any(word in content_lower for word in ['outage', 'downtime', 'unavailable']):
        classification['Impact'].append('service disruption')
    
    return classification

def main():
    """Main classification function"""
    # Get unclassified articles
    unclassified = RawArticle.objects.exclude(
        url__in=ClassifiedArticle.objects.values_list('url', flat=True)
    )
    
    print(f"Found {unclassified.count()} articles to classify")
    
    classified_count = 0
    for article in unclassified[:10]:  # Limit to 10 to avoid timeout
        try:
            # Get classification
            classification = simple_classify_article(article.content)
            
            # Create ClassifiedArticle
            ClassifiedArticle.objects.get_or_create(
                url=article.url,
                defaults={
                    'title': article.title,
                    'source': article.source.name,
                    'published': article.published,
                    'classification_source': 'ml',
                    'raw_content': article.content,
                    **classification
                }
            )
            
            classified_count += 1
            print(f"Classified: {article.title[:50]}...")
            
        except Exception as e:
            print(f"Error classifying article {article.id}: {e}")
    
    print(f"Successfully classified {classified_count} articles")

if __name__ == "__main__":
    main()