# views_similarity.py

from django.shortcuts import render
from llmintegration.faiss_query_utils import search_similar
from vtagent.models import RawArticle


def similarity_dashboard_view(request):
    query = request.GET.get("q", "phishing threat")
    results = search_similar(query_text=query, index_key="articles", top_k=5)

    enriched = []
    for record_id, text, score in results:
        try:
            article = RawArticle.objects.get(id=record_id)
            enriched.append({
                "title": article.title,
                "excerpt": article.content[:300] + "...",
                "score": round(score, 3)
            })
        except RawArticle.DoesNotExist:
            continue

    return render(request, "llmintegration/llm_similarity_dashboard.html", {
        "query": query,
        "results": enriched
    })
