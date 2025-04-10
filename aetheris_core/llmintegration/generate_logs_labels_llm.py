import os
import sys
import json
import pickle
import time
import django
from django.conf import settings
from django.db.models import Q

# Django setup
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aetheris_core.settings")
django.setup()

from vtagent.models import GeneratedTaxonomyLabel
from llmintegration.llm_utils import call_gemini

# Config
LOG_TYPES = ["siem", "xdr", "ids", "firewall", "edr", "hids", "application"]
FAISS_BASE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "faiss", "logs")
DATA_BASE = os.path.join(settings.BASE_DIR, "synthetic_data")
OUTPUT_DIR = os.path.join(settings.BASE_DIR, "llmintegration", "debug_outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Get taxonomy fields from model
EXHAUSTIVE_FIELDS = [
    f.name for f in GeneratedTaxonomyLabel._meta.get_fields()
    if f.name not in ("id", "raw_article", "record_id", "cmdb_item", "ad_user", "employee",
                      "labels_generated_at", "classification_source", "data_source", "data_origin")
       and not f.many_to_one
]

# Build prompt
def build_prompt(log_type, record_id, text):
    return f"""
You are a cybersecurity log classifier. Given the following {log_type.upper()} log entry, classify it across the fields below and return a JSON response with ONLY the fields listed.

Fields:
{json.dumps(EXHAUSTIVE_FIELDS, indent=2)}

Data Source: FAISS vectorized log text

### Log Entry ({record_id}):
{text}
""".strip()

# Normalize response
def parse_labels(raw):
    def parse_array(v):
        if isinstance(v, list): return v
        if isinstance(v, str) and v.strip(): return [v.strip()]
        return []
    return {
        "platform": parse_array(raw.get("platform")),
        "software": parse_array(raw.get("software")),
        "software_version": raw.get("software_version", ""),
        "os": raw.get("os", ""),
        "os_version": raw.get("os_version", ""),
        "security_software": raw.get("security_software", ""),
        "network_zone": raw.get("network_zone", ""),
        "ip_address": raw.get("ip_address", None),
        "country": raw.get("country", ""),
        "city": raw.get("city", ""),
        "business_unit": raw.get("business_unit", ""),
        "department": raw.get("department", ""),
        "severity": parse_array(raw.get("severity")),
        "impact": parse_array(raw.get("impact")),
        "actor": parse_array(raw.get("actor")),
        "origin": parse_array(raw.get("origin")),
        "compliance": parse_array(raw.get("compliance")),
        "threat_stage": raw.get("threat_stage", ""),
        "initial_access_method": raw.get("initial_access_method", ""),
        "payload_type": raw.get("payload_type", ""),
        "mitre_tactics": parse_array(raw.get("mitre_tactics")),
        "impact_area": parse_array(raw.get("impact_area")),
        "detection_vector": raw.get("detection_vector", ""),
        "reported_by": raw.get("reported_by", ""),
        "response_action": raw.get("response_action", ""),
    }

# Gemini-safe call wrapper
def safe_call_gemini(prompt, record_id):
    try:
        return call_gemini(prompt)
    except Exception as api_error:
        error_str = str(api_error)
        print(f"[!] Gemini API call failed for {record_id}: {error_str}")

        retry_seconds = 60
        if "retry_delay" in error_str:
            try:
                import re
                match = re.search(r"retry_delay\\s*{\\s*seconds:\\s*(\\d+)", error_str)
                if match:
                    retry_seconds = int(match.group(1))
            except:
                pass

        print(f"[⏳] Waiting {retry_seconds}s before retrying...")
        time.sleep(retry_seconds)

        try:
            return call_gemini(prompt)
        except Exception as retry_error:
            print(f"[!] Retry failed for {record_id}: {retry_error}")
            return None

# Main
def main():
    for log_type in LOG_TYPES:
        try:
            print(f"\n=== Processing {log_type.upper()} logs ===")
            id_map_path = os.path.join(FAISS_BASE, f"{log_type}.id_map.pkl")
            texts_path = os.path.join(FAISS_BASE, f"{log_type}.texts.pkl")

            with open(id_map_path, "rb") as f:
                id_map = pickle.load(f)
            with open(texts_path, "rb") as f:
                texts = pickle.load(f)

            record_lookup = dict(zip([f"{log_type.upper()}:{i}" for i in id_map], texts))

        except Exception as e:
            print(f"[!] Skipping {log_type.upper()}: Could not load FAISS files. {e}")
            continue

        for record_id, text in record_lookup.items():
            # Skip if already labeled
            if GeneratedTaxonomyLabel.objects.filter(
                Q(record_id=record_id),
                Q(data_origin="FAISS"),
                Q(classification_source="Gemini-LLM")
            ).exists():
                print(f"[↪] Skipping already labeled: {record_id}")
                continue

            try:
                print(f"[+] Sending to Gemini: {record_id}")
                prompt = build_prompt(log_type, record_id, text)

                # Delay between requests
                time.sleep(120)

                raw_response = safe_call_gemini(prompt, record_id)
                if not raw_response:
                    print(f"[!] Skipping {record_id} due to Gemini failure.")
                    continue

                cleaned = raw_response.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()

                if not cleaned.startswith("{"):
                    raise ValueError("Gemini returned non-JSON.")

                parsed = json.loads(cleaned)
                label_data = parse_labels(parsed)

                GeneratedTaxonomyLabel.objects.create(
                    record_id=record_id,
                    data_source=log_type.upper(),
                    data_origin="FAISS",
                    classification_source="Gemini-LLM",
                    **label_data
                )
                print(f"[✓] Saved: {record_id}")

            except Exception as e:
                print(f"[!] Failed: {record_id} — {e}")
                debug_path = os.path.join(OUTPUT_DIR, f"debug_{log_type}_{record_id.replace(':', '_')}.txt")
                with open(debug_path, "w", encoding="utf-8") as f:
                    f.write(f"Prompt:\\n{prompt}\\n\\nResponse:\\n{locals().get('raw_response', '[no response]')}")

if __name__ == "__main__":
    main()
