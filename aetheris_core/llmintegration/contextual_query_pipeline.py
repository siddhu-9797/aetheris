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


def build_gemini_prompt_and_response(user_query):
    filters = extract_filter_entities(user_query)
    query_vec = vectorizer.transform([user_query]).astype(np.float32).toarray()
    scores, indices = faiss_index.search(query_vec, 5)
    matched_ids = [id_map[i] for i in indices[0] if i < len(id_map)]
    articles = RawArticle.objects.filter(id__in=matched_ids)

    article_text = "\n\n".join([f"### {a.title}\n{a.content[:800]}..." for a in articles])
    record_ids = [f"Article:{a.id}" for a in articles]

    labels = list(GeneratedTaxonomyLabel.objects.all())
    if filters["city"]:
        labels = [l for l in labels if l.city.lower() == filters["city"].lower()]
    if filters["department"]:
        labels = [l for l in labels if l.department.lower() == filters["department"].lower()]
    grouped = summarize_labels(labels)

    label_summary = ""
    for key, counter in grouped.items():
        label_summary += f"\n**{key.title()}**:\n"
        for val, count in counter.most_common(10):
            label_summary += f"- {val}: {count}\n"

    assets = ConfigurationItem.objects.all()
    if filters["city"]:
        assets = assets.filter(city__iexact=filters["city"])
    if filters["department"]:
        assets = assets.filter(department__iexact=filters["department"])
    assets = assets[:50]

    asset_header = "| Type | OS | Email | Location |\n|------|----|--------|----------|"
    asset_table = "\n".join([
        f"| {a.asset_type} | {a.os} | {a.employee_email} | {a.city}, {a.country} |" for a in assets
    ])

    prompt_type = classify_prompt_type(user_query)

    prompt = f"""
You are a cybersecurity threat analyst. You have access to both external threat intel and internal organizational data.

### User Query:
{user_query}

### Articles (Summarized):
{article_text}

### Taxonomy Labels (Summarized by Category):
{label_summary}

### Internal Assets:
{asset_header}
{asset_table}

Please provide a response that includes:
- **## Summary** of threat impact
- **## Affected Assets** (use Markdown table if appropriate)
- **## Threat Types or Actors** (bulleted list)
- **## Recommended Actions** (if applicable)

Only include high-severity threats if possible.
Respond in Markdown.
"""

    return call_gemini(prompt)