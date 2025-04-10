# contextual_query_pipeline.py

from django.db.models import Q
from vtagent.models import RawArticle, GeneratedTaxonomyLabel
from syntheticcmdb.models import ConfigurationItem
from llmintegration.llm_utils import call_gemini
from sentence_transformers import SentenceTransformer, util
import faiss
import pickle
import os

EMBEDDING_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
INDEX_PATH = os.path.join("faiss", "articles", "index.index")
ID_MAP_PATH = os.path.join("faiss", "articles", "id_map.pkl")
TEXTS_PATH = os.path.join("faiss", "articles", "texts.pkl")

# Load FAISS index and mappings
faiss_index = faiss.read_index(INDEX_PATH)
with open(ID_MAP_PATH, "rb") as f:
    id_map = pickle.load(f)
with open(TEXTS_PATH, "rb") as f:
    texts = pickle.load(f)


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
    embedding = EMBEDDING_MODEL.encode(user_query, convert_to_tensor=True)
    top_k = 5
    scores, indices = faiss_index.search(embedding.unsqueeze(0).cpu().numpy(), top_k)
    matched_ids = [id_map[i] for i in indices[0] if i < len(id_map)]
    articles = RawArticle.objects.filter(id__in=matched_ids)

    article_text = "\n\n".join([f"Title: {a.title}\nContent: {a.content[:1000]}..." for a in articles])
    record_ids = [f"Article:{a.id}" for a in articles]

    labels = GeneratedTaxonomyLabel.objects.filter(record_id__in=record_ids)
    label_summary = "\n".join([
        f"ID: {l.record_id} | Impact: {l.impact} | Actor: {l.actor} | Platform: {l.platform}" for l in labels
    ])

    assets = ConfigurationItem.objects.filter(
        Q(asset_type__icontains="laptop") | Q(asset_type__icontains="server")
    )[:10]
    asset_list = "\n".join([
        f"{a.asset_type} - {a.os} - {a.owner_email} - {a.city}, {a.country}" for a in assets
    ])

    prompt_type = classify_prompt_type(user_query)

    if prompt_type == "summary":
        prompt = f"""
Summarize the following threat reports:

{article_text}

Include impacted systems and actors if available.
"""
    elif prompt_type == "impact":
        prompt = f"""
Identify affected assets and users based on this context:

{label_summary}

Known affected assets:
{asset_list}
"""
    elif prompt_type == "action":
        prompt = f"""
Given this threat context:

{article_text}

And related assets:
{asset_list}

Suggest appropriate remediation and containment steps.
"""
    else:
        prompt = f"""
You are a cybersecurity assistant. Here is current context:

{article_text}

Taxonomy:
{label_summary}

Assets:
{asset_list}

User Query: {user_query}
Please provide the best response based on available intelligence.
"""

    return call_gemini(prompt)
