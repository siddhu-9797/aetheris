# views_anomaly.py

from django.shortcuts import render
from llmintegration.faiss_query_utils import load_faiss_index
from vtagent.models import RawArticle, GeneratedTaxonomyLabel
from syntheticcmdb.models import ConfigurationItem


def anomaly_dashboard_view(request):
    data_type = request.GET.get("type", "articles")  # can be "articles" or "logs"
    index_path = data_type if data_type != "logs" else "logs/siem"

    # Load FAISS index + metadata
    index, id_map, texts = load_faiss_index(index_path)

    # Step 1: Run similarity search against all vectors themselves
    scores, indices = index.search(index.reconstruct_n(0, len(id_map)), 2)

    # Step 2: Select low similarity records (e.g. below threshold)
    threshold = 0.3
    low_sim_ids = [id_map[i] for i, sim in enumerate(scores[:, 1]) if sim < threshold]

    # Step 3: Pull low similarity articles/logs
    records = RawArticle.objects.filter(id__in=low_sim_ids) if data_type == "articles" else []
    matched_taxonomy = GeneratedTaxonomyLabel.objects.filter(record_id__in=[f"Article:{r.id}" for r in records])

    # Step 4: Map taxonomy to affected internal assets
    matched_platforms = set(p for label in matched_taxonomy for p in (label.platform or []))
    possible_assets = ConfigurationItem.objects.all()[:200]


    return render(request, "llmintegration/llm_anomaly_dashboard.html", {
        "records": records,
        "taxonomy": matched_taxonomy,
        "assets": possible_assets,
        "threshold": threshold,
        "data_type": data_type
    })
