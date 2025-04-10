# views_dashboard.py

from django.shortcuts import render
from django.db.models import Count
from vtagent.models import GeneratedTaxonomyLabel
import json
from collections import Counter


def llm_dashboard_view(request):
    # Total label volume by data source
    source_counts = (
        GeneratedTaxonomyLabel.objects
        .values("data_source")
        .annotate(count=Count("id"))
        .order_by("data_source")
    )

    # Classification source breakdown (LLM vs ML)
    classification_counts = (
        GeneratedTaxonomyLabel.objects
        .values("classification_source")
        .annotate(count=Count("id"))
        .order_by("classification_source")
    )

    # Recent label generation (last 10 by timestamp)
    recent_labels = (
        GeneratedTaxonomyLabel.objects
        .order_by("-labels_generated_at")[:10]
    )

    # Helper to flatten multivalued fields
    def flatten_field(field_name):
        all_values = []
        for label in GeneratedTaxonomyLabel.objects.exclude(**{field_name: None}):
            val = getattr(label, field_name)
            if isinstance(val, list):
                all_values.extend(val)
            elif val:
                all_values.append(val)
        return Counter(all_values).most_common(10)

    impact_data = flatten_field("impact")
    os_data = flatten_field("os")
    platform_data = flatten_field("platform")
    software_data = flatten_field("software")
    department_data = flatten_field("department")
    country_data = flatten_field("country")
    mitre_data = flatten_field("mitre_tactics")

    context = {
        "source_labels": json.dumps([x["data_source"] for x in source_counts]),
        "source_values": json.dumps([x["count"] for x in source_counts]),
        "class_labels": json.dumps([x["classification_source"] for x in classification_counts]),
        "class_values": json.dumps([x["count"] for x in classification_counts]),
        "recent_labels": recent_labels,
        "impact_labels": json.dumps([x[0] for x in impact_data]),
        "impact_values": json.dumps([x[1] for x in impact_data]),
        "os_labels": json.dumps([x[0] for x in os_data]),
        "os_values": json.dumps([x[1] for x in os_data]),
        "platform_labels": json.dumps([x[0] for x in platform_data]),
        "platform_values": json.dumps([x[1] for x in platform_data]),
        "software_labels": json.dumps([x[0] for x in software_data]),
        "software_values": json.dumps([x[1] for x in software_data]),
        "department_labels": json.dumps([x[0] for x in department_data]),
        "department_values": json.dumps([x[1] for x in department_data]),
        "country_labels": json.dumps([x[0] for x in country_data]),
        "country_values": json.dumps([x[1] for x in country_data]),
        "mitre_labels": json.dumps([x[0] for x in mitre_data]),
        "mitre_values": json.dumps([x[1] for x in mitre_data])
    }

    return render(request, "llmintegration/llm_dashboard.html", context)
