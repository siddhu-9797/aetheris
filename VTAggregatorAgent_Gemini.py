# VTAggregatorAgent-Gemini.py
# Purpose: Classify cybersecurity articles using Google Gemini API (LLM-based classification)

import json
import os
from dotenv import load_dotenv
import logging
from datetime import datetime
from tqdm import tqdm
import google.generativeai as genai

# === Configure Gemini ===
#load_dotenv()
api_key = os.getenv("GOOGLE_GEMINI_API_KEY", "").strip().strip('"')
print(f"Loaded Gemini API key (first 10 chars): {api_key[:10] if api_key else 'NOT FOUND'}")
if not api_key:
    raise ValueError("GOOGLE_GEMINI_API_KEY is missing or invalid.")

genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-1.5-flash")

# === Logging setup ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VTAggregatorAgent-Gemini")

# === V&T classification schema ===
CATEGORIES = {
    "VT_PrimaryType": ["vulnerability", "threat", "exploit"],
    "VT_Subtype": ["ransomware", "phishing", "malware", "sql injection", "xss", "zero-day"],
    "Industry": ["finance", "healthcare", "energy", "technology", "government", "critical infrastructure"],
    "Platform": ["cloud", "endpoint", "network", "web application", "operating system", "iot", "industrial control systems"],
    "Severity": ["critical", "high", "medium", "low", "data breach", "service disruption", "financial loss"],
    "Actor": ["cybercriminal", "insider threat", "state-sponsored", "external", "internal"],
    "Compliance": ["gdpr", "hipaa", "nist", "iso27001", "star-fs", "cbest"]
}

# === Load articles ===
def load_articles(files):
    url_to_article = {}
    for file in files:
        logger.info(f"Loading {file}")
        with open(file, "r", encoding="utf-8") as f:
            data = json.load(f)
            for article in data:
                url = article.get("url")
                content = article.get("content", "")
                if url:
                    if url in url_to_article:
                        existing_len = len(url_to_article[url].get("content", ""))
                        if len(content) > existing_len:
                            url_to_article[url] = article
                    else:
                        url_to_article[url] = article
    return list(url_to_article.values())

# === Prompt LLM for classification ===
def classify_with_gemini(content, max_tokens=4000):
    prompt = f"""
You are a cybersecurity analyst AI. Read the article content and classify it into the following categories. Only use the listed values.
Return a JSON object with exactly these fields:

{json.dumps(CATEGORIES, indent=2)}

Content:
"""

    try:
        full_prompt = prompt + content[:max_tokens]
        response = model.generate_content(full_prompt)

        if not response or not hasattr(response, "text"):
            raise ValueError("Gemini response missing text field.")

        output = response.text.strip()

        if not output:
            raise ValueError("Gemini returned empty response.")

        # DEBUG: Log a preview
        logger.debug(f"Gemini raw output preview: {output[:300]}")

        return json.loads(output)

    except Exception as e:
        logger.warning(f"Gemini classification failed: {e}")

        # Optional: write bad samples to a debug file
        with open("gemini_errors.log", "a", encoding="utf-8") as f:
            f.write(f"---\nError: {str(e)}\nContent Preview: {content[:300]}\n---\n\n")

        return {}

# === Main ===
def aggregate():
    input_files = ["crawled_articles_Scrapy.json", "crawled_articles_BeautifulSoup.json"]
    articles = load_articles(input_files)
    logger.info(f"Loaded {len(articles)} deduplicated articles.")

    results = []

    for article in tqdm(articles, desc="Gemini Classification"):
        content = article.get("content", "")
        if not content or len(content.strip()) < 100:
            logger.warning(f"Skipping article with short or weak content: {article.get('url')}")
            continue

        classification = classify_with_gemini(content)

        result = {
            "url": article.get("url"),
            "title": article.get("title"),
            "source": article.get("source"),
            "published": article.get("published"),
            "raw_content": content[:5000],
            "processed_at": str(datetime.now()),
        }
        result.update(classification)
        results.append(result)

    with open("classified_articles_gemini.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=4)
    logger.info("Saved Gemini-classified results to classified_articles_gemini.json")

if __name__ == "__main__":
    aggregate()
