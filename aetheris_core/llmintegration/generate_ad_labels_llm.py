import os
import sys
import json
import django
import pickle
import faiss
import numpy as np
from django.conf import settings

# === Django setup ===
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aetheris_core.settings")
django.setup()

from syntheticad.models import ADUser, ADGroup, ServiceAccount, DomainController
from vtagent.models import GeneratedTaxonomyLabel
from llmintegration.llm_utils import call_gemini

# === FAISS Paths ===
FAISS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "faiss", "ad")

with open(os.path.join(FAISS_DIR, "id_map.pkl"), "rb") as f:
    id_map = pickle.load(f)
with open(os.path.join(FAISS_DIR, "texts.pkl"), "rb") as f:
    all_texts = pickle.load(f)

id_map_lookup = dict(zip(id_map, all_texts))

# === Output Directory ===
OUTPUT_DIR = os.path.join(settings.BASE_DIR, "llmintegration", "debug_outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# === Taxonomy fields from model ===
EXHAUSTIVE_FIELDS = [
    field.name for field in GeneratedTaxonomyLabel._meta.get_fields()
    if field.name not in (
        "id", "raw_article", "record_id", "cmdb_item", "ad_user", "employee",
        "labels_generated_at", "classification_source", "data_source", "data_origin"
    ) and not field.many_to_one
]

# === Prompt builder ===
def build_prompt(record_id, origin, text_block):
    origin_note = "This data is from FAISS vector similarity." if origin == "FAISS" else "This data is from the Django database."
    return f"""
You are a cybersecurity identity classification engine. Given the following AD entity profile, classify it across the fields below and return a JSON response with ONLY the fields listed.

Fields:
{json.dumps(EXHAUSTIVE_FIELDS, indent=2)}

{origin_note}

### Entity Record ({record_id}):
{text_block}
""".strip()

# === Field parser ===
def parse_labels(json_output):
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

# === Main logic ===
def process_model(model_cls, model_name, limit=50):
    records = model_cls.objects.all()[:limit]

    for origin in ["Django", "FAISS"]:
        for obj in records:
            record_id = f"{model_name}:{obj.id}"

            if origin == "Django":
                text_block = str(obj)
            else:
                text_block = id_map_lookup.get(record_id, f"[FAISS text not found for {record_id}]")

            prompt = build_prompt(record_id, origin, text_block)

            try:
                print(f"[+] Processing {record_id} ({origin})")
                raw_response = call_gemini(prompt)

                cleaned_response = raw_response.strip()
                if cleaned_response.startswith("```json"):
                    cleaned_response = cleaned_response.removeprefix("```json").removesuffix("```").strip()
                elif cleaned_response.startswith("```"):
                    cleaned_response = cleaned_response.removeprefix("```").removesuffix("```").strip()

                if not cleaned_response.startswith("{"):
                    raise ValueError("Gemini response is not valid JSON.")

                parsed_json = json.loads(cleaned_response)
                label_data = parse_labels(parsed_json)

                GeneratedTaxonomyLabel.objects.create(
                    record_id=record_id,
                    classification_source="Gemini-LLM",
                    data_source=model_name,
                    data_origin=origin,
                    **label_data
                )
                print(f"[✓] Saved to DB: {record_id} ({origin})")

            except Exception as e:
                print(f"[!] Failed on {record_id} ({origin}): {e}")
                debug_file = os.path.join(OUTPUT_DIR, f"debug_{model_name}_{obj.id}_{origin}.txt")
                with open(debug_file, "w", encoding="utf-8") as f:
                    f.write(f"Prompt:\n{prompt}\n\nRaw Response:\n{raw_response}\n")

# === Run for all AD models ===
if __name__ == "__main__":
    process_model(ADUser, "ADUser")
    process_model(ADGroup, "ADGroup")
    process_model(ServiceAccount, "ServiceAccount")
    process_model(DomainController, "DomainController")
