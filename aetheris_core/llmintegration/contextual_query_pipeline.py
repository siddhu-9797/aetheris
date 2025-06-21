# contextual_query_pipeline.py

from django.db.models import Q
from vtagent.models import RawArticle, GeneratedTaxonomyLabel
from syntheticcmdb.models import ConfigurationItem
from llmintegration.llm_utils import call_gemini
import faiss
import pickle
import os
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from collections import Counter, defaultdict

# Paths
INDEX_PATH = os.path.join("faiss", "articles", "index.index")
ID_MAP_PATH = os.path.join("faiss", "articles", "id_map.pkl")
TEXTS_PATH = os.path.join("faiss", "articles", "texts.pkl")
VECTORIZER_PATH = os.path.join("faiss", "articles", "vectorizer.pkl")

# Load FAISS index and associated mappings
faiss_index = faiss.read_index(INDEX_PATH)
with open(ID_MAP_PATH, "rb") as f:
    id_map = pickle.load(f)
with open(TEXTS_PATH, "rb") as f:
    texts = pickle.load(f)
with open(VECTORIZER_PATH, "rb") as f:
    vectorizer: TfidfVectorizer = pickle.load(f)


def classify_prompt_type(query: str) -> str:
    query = query.lower()
    if any(x in query for x in ["remediation", "response", "contain", "fix"]):
        return "action"
    elif any(x in query for x in ["summary", "overview", "what is", "explain"]):
        return "summary"
    elif any(x in query for x in ["who is affected", "assets", "users", "employees"]):
        return "impact"
    elif any(x in query for x in ["how many", "count", "number of", "total"]):
        return "inventory"
    return "general"


def extract_filter_entities(query):
    query = query.lower()
    cities = ["berlin", "london", "frankfurt", "osaka", "edinburgh", "manchester"]
    departments = ["finance", "hr", "engineering", "it", "devops", "security"]
    found = {"city": None, "department": None}
    for city in cities:
        if city in query:
            found["city"] = city.title()
    for dept in departments:
        if dept in query:
            found["department"] = dept.title()
    return found


def summarize_labels(labels):
    groups = defaultdict(Counter)
    for l in labels:
        if isinstance(l.platform, list):
            groups["platform"].update(l.platform)
        if isinstance(l.os, str):
            groups["os"].update([l.os])
        if isinstance(l.department, str):
            groups["department"].update([l.department])
        if isinstance(l.country, str):
            groups["country"].update([l.country])
        if isinstance(l.city, str):
            groups["city"].update([l.city])
        if isinstance(l.severity, list):
            groups["severity"].update(l.severity)
        if isinstance(l.impact, list):
            groups["impact"].update(l.impact)
        if isinstance(l.actor, list):
            groups["actor"].update(l.actor)
        if isinstance(l.mitre_tactics, list):
            groups["mitre_tactics"].update(l.mitre_tactics)
    return groups


def extract_time_filter(query):
    """Extract time-based filters from query"""
    query = query.lower()
    from datetime import datetime, timedelta
    now = datetime.now()
    
    if any(x in query for x in ["last 24 hours", "past 24 hours", "today"]):
        return now - timedelta(hours=24)
    elif any(x in query for x in ["last week", "past week"]):
        return now - timedelta(days=7)
    elif any(x in query for x in ["last month", "past month"]):
        return now - timedelta(days=30)
    return None

def handle_inventory_query(user_query, filters, conversation_history=None):
    """Handle asset inventory and counting queries"""
    from collections import Counter
    from syntheticad.models import ADUser, ADGroup, ServiceAccount
    from syntheticemployees.models import Employee
    
    query_lower = user_query.lower()
    
    # Detect if asking about users/people
    if any(x in query_lower for x in ["user", "users", "people", "employee", "employees", "account", "accounts"]):
        return handle_user_inventory_query(user_query, filters, conversation_history)
    
    # Otherwise handle asset inventory
    assets = ConfigurationItem.objects.all()
    if filters["city"]:
        assets = assets.filter(city__iexact=filters["city"])
    if filters["department"]:
        assets = assets.filter(department__iexact=filters["department"])
    
    # Count by asset type
    asset_counts = Counter(assets.values_list('asset_type', flat=True))
    
    # Build summary table
    total_assets = assets.count()
    server_count = assets.filter(asset_type__icontains="server").count()
    
    asset_breakdown = "| Asset Type | Count |\n|------------|-------|\n"
    for asset_type, count in asset_counts.most_common(10):
        asset_breakdown += f"| {asset_type} | {count} |\n"
    
    # Location breakdown
    location_counts = Counter()
    for asset in assets.values('city', 'country'):
        location_counts[f"{asset['city']}, {asset['country']}"] += 1
    
    location_breakdown = "| Location | Assets |\n|----------|--------|\n"
    for location, count in location_counts.most_common(5):
        location_breakdown += f"| {location} | {count} |\n"
    
    # Build conversation context if available
    context_section = ""
    if conversation_history and len(conversation_history) > 0:
        recent_history = conversation_history[-4:]  # Last 2 exchanges
        context_section = "\n### Conversation Context:\n"
        for msg in recent_history:
            if msg["role"] == "chat-user":
                context_section += f"**Previous User:** {msg['text']}\n"
            elif msg["role"] == "chat-bot":
                # Use raw text if available, otherwise clean the HTML/markdown
                if 'text' in msg:
                    clean_text = msg['text'][:150]
                else:
                    clean_text = msg.get('text_html', '').replace('<p>', '').replace('</p>', '').replace('**', '').replace('#', '')[:150]
                context_section += f"**Previous Response:** {clean_text}...\n"
        context_section += f"\n**Current User Query:** {user_query}\n"
    else:
        context_section = f"\n### User Query:\n{user_query}\n"

    prompt = f"""
You are Aetheris Asset Intelligence Assistant. The user is asking about organizational asset inventory.

{context_section}

### Asset Inventory Summary:
- **Total Assets**: {total_assets}
- **Servers**: {server_count}
- **Other Infrastructure**: {total_assets - server_count}

### Asset Breakdown by Type:
{asset_breakdown}

### Geographic Distribution:
{location_breakdown}

IMPORTANT: If this is a follow-up question, refer to the conversation context above and provide relevant comparisons or additional details based on the previous discussion.

Provide a clear, concise response about the organization's IT infrastructure. Focus on answering the specific question while providing relevant context about the asset landscape.

Format response in clean Markdown.
"""
    
    return call_gemini(prompt)

def handle_user_inventory_query(user_query, filters, conversation_history=None):
    """Handle user/employee inventory queries"""
    from collections import Counter
    from syntheticad.models import ADUser, ADGroup, ServiceAccount
    from syntheticemployees.models import Employee
    
    # Get user data
    ad_users = ADUser.objects.all()
    employees = Employee.objects.all()
    ad_groups = ADGroup.objects.all()
    service_accounts = ServiceAccount.objects.all()
    
    # Apply filters
    if filters["city"]:
        ad_users = ad_users.filter(country__icontains=filters["city"])
        employees = employees.filter(city__iexact=filters["city"])
    if filters["department"]:
        ad_users = ad_users.filter(department__iexact=filters["department"])
        employees = employees.filter(department__iexact=filters["department"])
    
    # Count breakdowns
    dept_counts = Counter(ad_users.values_list('department', flat=True))
    location_counts = Counter(ad_users.values_list('country', flat=True))
    
    # Build tables
    dept_breakdown = "| Department | Users |\n|------------|-------|\n"
    for dept, count in dept_counts.most_common(10):
        dept_breakdown += f"| {dept} | {count} |\n"
    
    location_breakdown = "| Location | Users |\n|----------|-------|\n"
    for location, count in location_counts.most_common(5):
        location_breakdown += f"| {location} | {count} |\n"
    
    # Build conversation context if available
    context_section = ""
    if conversation_history and len(conversation_history) > 0:
        recent_history = conversation_history[-4:]  # Last 2 exchanges
        context_section = "\n### Conversation Context:\n"
        for msg in recent_history:
            if msg["role"] == "chat-user":
                context_section += f"**Previous User:** {msg['text']}\n"
            elif msg["role"] == "chat-bot":
                # Use raw text if available, otherwise clean the HTML/markdown
                if 'text' in msg:
                    clean_text = msg['text'][:150]
                else:
                    clean_text = msg.get('text_html', '').replace('<p>', '').replace('</p>', '').replace('**', '').replace('#', '')[:150]
                context_section += f"**Previous Response:** {clean_text}...\n"
        context_section += f"\n**Current User Query:** {user_query}\n"
    else:
        context_section = f"\n### User Query:\n{user_query}\n"

    prompt = f"""
You are Aetheris Identity & Access Management Assistant. The user is asking about organizational user accounts and identity management.

{context_section}

### User Account Summary:
- **Total AD Users**: {ad_users.count()}
- **Total Employees**: {employees.count()}
- **AD Groups**: {ad_groups.count()}
- **Service Accounts**: {service_accounts.count()}

### Users by Department:
{dept_breakdown}

### Users by Location:
{location_breakdown}

IMPORTANT: If this is a follow-up question, refer to the conversation context above and provide relevant comparisons or additional details based on the previous discussion.

Provide a clear, direct answer to the user's question about user accounts. Include relevant organizational context and identity management insights.

Format response in clean Markdown.
"""
    
    return call_gemini(prompt)

def build_gemini_prompt_and_response(user_query, conversation_history=None):
    filters = extract_filter_entities(user_query)
    time_filter = extract_time_filter(user_query)
    prompt_type = classify_prompt_type(user_query)
    
    # For inventory queries, focus on assets rather than articles
    if prompt_type == "inventory":
        return handle_inventory_query(user_query, filters, conversation_history)
    
    # Enhance query with conversation context for better vector search
    enhanced_query = user_query
    context_keywords = []
    
    if conversation_history and len(conversation_history) > 0:
        # Extract important keywords from recent conversation
        recent_messages = conversation_history[-4:]  # Last 2 exchanges
        for msg in recent_messages:
            text = msg.get('text', '').lower()
            # Extract threat-related keywords
            if 'webdav' in text or 'zero-day' in text:
                context_keywords.extend(['webdav', 'zero-day', 'microsoft'])
            if 'apple' in text and 'cve' in text:
                context_keywords.extend(['apple', 'cve', 'zero-click'])
            if 'fortinet' in text:
                context_keywords.extend(['fortinet', 'fortigate'])
            if 'ransomware' in text:
                context_keywords.extend(['ransomware', 'malware'])
        
        # Add context keywords to enhance search
        if context_keywords:
            enhanced_query = user_query + " " + " ".join(set(context_keywords))
    
    # Optional: Add debug logging when needed
    # print(f"[DEBUG PIPELINE] Enhanced query: {enhanced_query}")
    # print(f"[DEBUG PIPELINE] Context keywords: {context_keywords}")
    
    # Try multiple search strategies
    query_vec = vectorizer.transform([enhanced_query]).astype(np.float32).toarray()
    scores, indices = faiss_index.search(query_vec, 20)  # Get more results for better filtering
    matched_ids = [id_map[i] for i in indices[0] if i < len(id_map)]
    
    # If we have context keywords, also try a direct keyword search
    if context_keywords:
        keyword_query = " ".join(context_keywords)
        keyword_vec = vectorizer.transform([keyword_query]).astype(np.float32).toarray()
        keyword_scores, keyword_indices = faiss_index.search(keyword_vec, 10)
        keyword_matched_ids = [id_map[i] for i in keyword_indices[0] if i < len(id_map)]
        
        # Combine results, prioritizing keyword matches
        all_matched_ids = list(dict.fromkeys(keyword_matched_ids + matched_ids))  # Remove duplicates, keep order
        matched_ids = all_matched_ids[:15]  # Limit to reasonable number
    
    # Get articles but preserve FAISS ordering (most relevant first)
    articles_dict = {a.id: a for a in RawArticle.objects.filter(id__in=matched_ids)}
    articles = [articles_dict[aid] for aid in matched_ids if aid in articles_dict]
    
    # Apply time filter while preserving order
    if time_filter:
        articles = [a for a in articles if a.scraped_at >= time_filter]
    
    # Boost articles that contain context keywords in title or content
    if context_keywords:
        # First, try to find articles from our search that match context
        boosted_articles = []
        other_articles = []
        
        for article in articles:
            article_text = (article.title + " " + article.content).lower()
            matches_context = any(keyword in article_text for keyword in context_keywords)
            if matches_context:
                boosted_articles.append(article)
            else:
                other_articles.append(article)
        
        # If we didn't find enough context-relevant articles, do a direct database search
        if len(boosted_articles) < 2:
            for keyword in context_keywords:
                if keyword in ['webdav', 'zero-day', 'microsoft']:
                    # Direct database search for this specific keyword
                    direct_matches = RawArticle.objects.filter(
                        content__icontains=keyword
                    ).order_by('-scraped_at')[:3]
                    
                    for article in direct_matches:
                        if article not in boosted_articles:
                            boosted_articles.append(article)
        
        # Prioritize context-relevant articles
        articles = (boosted_articles + other_articles)[:5]
    else:
        articles = articles[:5]  # Limit to top 5 after filtering

    # Extract threat indicators from articles to correlate with assets
    threat_keywords = []
    for article in articles:
        content_lower = article.content.lower()
        if any(x in content_lower for x in ["globalprotect", "palo alto", "pan-os"]):
            threat_keywords.extend(["palo alto", "globalprotect", "pan-os"])
        if any(x in content_lower for x in ["windows", "microsoft"]):
            threat_keywords.extend(["windows", "microsoft"])
        if any(x in content_lower for x in ["linux", "ubuntu", "redhat"]):
            threat_keywords.extend(["linux"])
        if any(x in content_lower for x in ["vpn", "gateway", "firewall"]):
            threat_keywords.extend(["vpn", "firewall"])
    
    # Generate article text for LLM prompt
    article_text = "\n\n".join([f"### {a.title}\n**Source:** {a.source.name}\n**Published:** {a.published}\n**URL:** {a.url}\n{a.content[:800]}..." for a in articles])

    # Get taxonomy labels for the matched articles specifically
    article_ids = [a.id for a in articles]
    labels = GeneratedTaxonomyLabel.objects.filter(raw_article_id__in=article_ids)
    if filters["city"]:
        labels = labels.filter(city__icontains=filters["city"])
    if filters["department"]:
        labels = labels.filter(department__icontains=filters["department"])
    
    # Also get general organizational labels for context
    general_labels = GeneratedTaxonomyLabel.objects.exclude(raw_article_id__in=article_ids)[:20]
    all_labels = list(labels) + list(general_labels)
    grouped = summarize_labels(all_labels)

    label_summary = ""
    for key, counter in grouped.items():
        label_summary += f"\n**{key.title()}**:\n"
        for val, count in counter.most_common(10):
            label_summary += f"- {val}: {count}\n"

    # Correlate assets based on threat indicators
    assets = ConfigurationItem.objects.all()
    if filters["city"]:
        assets = assets.filter(city__iexact=filters["city"])
    if filters["department"]:
        assets = assets.filter(department__iexact=filters["department"])
    
    # Filter assets based on threat relevance
    relevant_assets = []
    for asset in assets:
        is_relevant = False
        for keyword in threat_keywords:
            if (keyword in asset.asset_type.lower() or 
                keyword in asset.os.lower() or 
                keyword in str(asset.software).lower() or
                keyword in asset.security_software.lower()):
                is_relevant = True
                break
        if is_relevant:
            relevant_assets.append(asset)
    
    # If no specific correlation, show sample of all assets
    if not relevant_assets:
        relevant_assets = list(assets[:20])
    else:
        relevant_assets = relevant_assets[:20]

    asset_header = "| Type | OS | Email | Location | Software |\n|------|----|---------|-----------|---------| "
    asset_table = "\n".join([
        f"| {a.asset_type} | {a.os} | {a.employee_email} | {a.city}, {a.country} | {', '.join(a.software[:2]) if a.software else 'N/A'} |" 
        for a in relevant_assets
    ])

    # Count relevant vs total assets for context
    total_assets = assets.count()
    relevant_count = len(relevant_assets)
    
    # Generate source attribution
    sources_info = []
    for article in articles:
        sources_info.append(f"- **{article.source.name}**: {article.title} ({article.published})")
    source_attribution = "\n".join(sources_info) if sources_info else "No recent sources found"

    # Build conversation context if available
    context_section = ""
    if conversation_history and len(conversation_history) > 0:
        # Get last few exchanges for context
        recent_history = conversation_history[-6:]  # Last 3 exchanges (user + bot pairs)
        context_section = "\n### Conversation Context:\n"
        
        # Build context section from conversation history
        for i, msg in enumerate(recent_history):
            if msg["role"] == "chat-user":
                context_section += f"**Previous User:** {msg['text']}\n"
            elif msg["role"] == "chat-bot":
                # Use raw text if available, otherwise clean the HTML/markdown
                if 'text' in msg:
                    clean_text = msg['text'][:200]
                else:
                    # Fallback to cleaning HTML/markdown
                    clean_text = msg.get('text_html', '').replace('<p>', '').replace('</p>', '').replace('**', '').replace('#', '')[:200]
                context_section += f"**Previous Response:** {clean_text}...\n"
        
        context_section += "\n**Current User Query:** " + user_query + "\n"
    else:
        context_section = f"\n### User Query:\n{user_query}\n"

    prompt = f"""
You are Aetheris Threat Intelligence Assistant, an advanced cybersecurity analyst with access to external threat intelligence and internal organizational data.

{context_section}

### Recent Threat Intelligence Sources:
{source_attribution}

### Threat Articles Analysis:
{article_text}

### Organizational Context:
{label_summary}

### Potentially Affected Internal Assets ({relevant_count}/{total_assets} assets shown):
{asset_header}
{asset_table}

Please provide a comprehensive threat analysis including:
- **## Summary** - Key threat overview and potential organizational impact
- **## Affected Assets** - Specific assets at risk based on the threat indicators
- **## Threat Actors & TTPs** - Known threat actors and their tactics, techniques, procedures
- **## Recommended Actions** - Prioritized mitigation and response steps
- **## Sources** - Attribution to specific threat intelligence sources

IMPORTANT: If this is a follow-up question, refer to the conversation context above and build upon previous responses. Maintain continuity and reference earlier points when relevant.

Focus on high-severity threats and provide actionable intelligence.
Format response in clean Markdown.
"""

    # Optional: Add debug logging when needed for troubleshooting
    # print(f"[DEBUG PIPELINE] Final prompt length: {len(prompt)}")
    # print(f"[DEBUG PIPELINE] Articles included: {len(articles)}")

    return call_gemini(prompt)