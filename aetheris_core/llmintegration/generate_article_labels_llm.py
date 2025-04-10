import os
import sys
import json
import django
from datetime import datetime
from django.conf import settings

# === Django setup ===
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aetheris_core.settings")
django.setup()

from vtagent.models import RawArticle, GeneratedTaxonomyLabel
from llmintegration.llm_utils import call_gemini

# === Paths & config ===
OUTPUT_DIR = os.path.join(settings.BASE_DIR, "llmintegration", "debug_outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

SAVE_TO_DB = True
SAVE_TO_JSON = True
MAX_ARTICLES = 100

# === Dynamically generate EXHAUSTIVE_FIELDS from model ===
EXHAUSTIVE_FIELDS = [
    field.name for field in GeneratedTaxonomyLabel._meta.get_fields()
    if field.name not in (
        "id", "raw_article", "record_id", "cmdb_item", "ad_user", "employee",
        "labels_generated_at", "classification_source", "data_source", "data_origin"
    ) and not field.many_to_one
]

# === Prompt builder ===
def build_prompt(article: RawArticle, origin: str) -> str:
    origin_note = "This data was derived from FAISS-based similarity context." if origin == "FAISS" else "This data is directly from the structured Django model."
    return f"""
You are a cybersecurity threat classification engine. Given the following article, classify it across the fields below and return a JSON response with ONLY the fields listed.

Fields:
{json.dumps(EXHAUSTIVE_FIELDS, indent=2)}

{origin_note}

### Article Title:
{article.title}

### Article Content:
{article.content[:4000]}
""".strip()

# === Safe field parser ===
def parse_labels(json_output: dict) -> dict:
    def parse_array(val):
        if isinstance(val, list):
            return val
        if isinstance(val, str) and val.strip():
            return [val.strip()]
        return []

    return {
        "platform": parse_array(json_output.get("platform")),
        "software": parse_array(json_output.get("software")),
        "software_version": json_output.get("software_version", ""),
        "os": json_output.get("os", ""),
        "os_version": json_output.get("os_version", ""),
        "security_software": json_output.get("security_software", ""),
        "network_zone": json_output.get("network_zone", ""),
        "ip_address": json_output.get("ip_address", None),
        "country": json_output.get("country", ""),
        "city": json_output.get("city", ""),
        "business_unit": json_output.get("business_unit", ""),
        "department": json_output.get("department", ""),
        "severity": parse_array(json_output.get("severity")),
        "impact": parse_array(json_output.get("impact")),
        "actor": parse_array(json_output.get("actor")),
        "origin": parse_array(json_output.get("origin")),
        "compliance": parse_array(json_output.get("compliance")),
        "threat_stage": json_output.get("threat_stage", ""),
        "initial_access_method": json_output.get("initial_access_method", ""),
        "payload_type": json_output.get("payload_type", ""),
        "mitre_tactics": parse_array(json_output.get("mitre_tactics")),
        "impact_area": parse_array(json_output.get("impact_area")),
        "detection_vector": json_output.get("detection_vector", ""),
        "reported_by": json_output.get("reported_by", ""),
        "response_action": json_output.get("response_action", ""),
    }

# === Main runner ===
def main():
    articles = RawArticle.objects.all().order_by("id")[:MAX_ARTICLES]
    results = []

    for origin in ["Django", "FAISS"]:
        for article in articles:
            try:
                print(f"[+] Processing Article #{article.id} with {origin}")
                prompt = build_prompt(article, origin)
                raw_response = call_gemini(prompt)

                # Clean markdown-wrapped JSON
                cleaned_response = raw_response.strip()
                if cleaned_response.startswith("```json"):
                    cleaned_response = cleaned_response.removeprefix("```json").removesuffix("```").strip()
                elif cleaned_response.startswith("```"):
                    cleaned_response = cleaned_response.removeprefix("```").removesuffix("```").strip()

                if not cleaned_response.startswith("{"):
                    raise ValueError("Gemini response is not valid JSON.")

                parsed_json = json.loads(cleaned_response)
                label_data = parse_labels(parsed_json)

                if SAVE_TO_DB:
                    GeneratedTaxonomyLabel.objects.create(
                        raw_article=article,
                        classification_source="Gemini-LLM",
                        data_source="RawArticle",
                        data_origin=origin,
                        **label_data
                    )
                    print(f"[✓] Saved to DB: Article #{article.id} ({origin})")

                results.append({
                    "article_id": article.id,
                    "title": article.title,
                    "origin": origin,
                    "labels": label_data
                })

            except Exception as e:
                print(f"[!] Failed on Article #{article.id} ({origin}): {e}")
                debug_path = os.path.join(OUTPUT_DIR, f"debug_article_{article.id}_{origin}.txt")
                with open(debug_path, "w", encoding="utf-8") as f:
                    f.write(f"Prompt:\n{prompt}\n\nRaw Response:\n{raw_response}\n\nCleaned:\n{locals().get('cleaned_response', '[none]')}")

    if SAVE_TO_JSON:
        output_path = os.path.join(OUTPUT_DIR, "article_labels_gemini.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        print(f"[✓] JSON output saved to {output_path}")

if __name__ == "__main__":
    main()
