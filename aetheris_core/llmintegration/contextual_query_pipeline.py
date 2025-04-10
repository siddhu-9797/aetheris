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


def build_gemini_prompt_and_response(user_query):
    query_vec = vectorizer.transform([user_query]).astype(np.float32).toarray()
    scores, indices = faiss_index.search(query_vec, 5)
    matched_ids = [id_map[i] for i in indices[0] if i < len(id_map)]
    articles = RawArticle.objects.filter(id__in=matched_ids)

    article_text = "\n\n".join([f"### {a.title}\n{a.content[:800]}..." for a in articles])
    record_ids = [f"Article:{a.id}" for a in articles]

    labels = GeneratedTaxonomyLabel.objects.filter(record_id__in=record_ids)
    label_summary = "\n".join([
        f"- **{l.record_id}** | Impact: {l.impact} | Actor: {l.actor} | Platform: {l.platform}" for l in labels
    ])

    assets = ConfigurationItem.objects.filter(
        Q(asset_type__icontains="laptop") | Q(asset_type__icontains="server")
    )[:10]
    asset_table = "\n".join([
        f"| {a.asset_type} | {a.os} | {a.employee_email} | {a.city}, {a.country} |" for a in assets
    ])
    asset_header = "| Type | OS | Email | Location |\n|------|----|--------|----------|"

    prompt_type = classify_prompt_type(user_query)

    if prompt_type == "summary":
        prompt = f"""
### Threat Summary Report

{article_text}

Include impacted systems and actors. Format output using:
- Headings (##)
- Bullet lists
- Markdown tables for structured info
"""
    elif prompt_type == "impact":
        prompt = f"""
### Affected Systems & Users

Taxonomy Labels:
{label_summary}

#### Assets Table (format in Markdown):
{asset_header}
{asset_table}
"""
    elif prompt_type == "action":
        prompt = f"""
### Recommended Remediation Steps

Threat Context:
{article_text}

Assets involved:
{asset_header}
{asset_table}

Provide actionable next steps.
"""
    else:
        prompt = f"""
### General Cybersecurity Query

Articles:
{article_text}

Labels:
{label_summary}

Assets:
{asset_header}
{asset_table}

User Query: {user_query}

Respond appropriately in structured format.
"""

    return call_gemini(prompt)
