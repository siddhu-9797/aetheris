import json
import pandas as pd
from transformers import pipeline
from tqdm import tqdm
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VTAggregatorAgent")

# === 1. Define taxonomies ===
vt_primary_types = ["vulnerability", "threat", "exploit"]
vt_subtypes = ["ransomware", "phishing", "malware", "sql injection", "xss", "zero-day"]
industries = ["finance", "healthcare", "energy", "technology", "government", "critical infrastructure"]
platforms = ["cloud", "endpoint", "network", "web application", "operating system", "iot", "industrial control systems"]
severities = ["critical", "high", "medium", "low", "data breach", "service disruption", "financial loss"]
actors = ["cybercriminal", "insider threat", "state-sponsored", "external", "internal"]
compliance_tags = ["gdpr", "hipaa", "nist", "iso27001", "star-fs", "cbest"]

# === 2. Smarter loader: prefers longer content across duplicates ===
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

# === 3. Robust classifier ===
def classify_article(zero_shot, content, labels):
    try:
        if not content or not labels:
            return []
        result = zero_shot(content, labels, multi_label=True)
        predictions = {label: score for label, score in zip(result["labels"], result["scores"])}
        top_tags = [label for label, score in predictions.items() if score > 0.4]
        return top_tags
    except Exception as e:
        logger.warning(f"Classification failed: {e}")
        return []

# === 4. Core function ===
def aggregate_and_classify():
    input_files = ["crawled_articles_Scrapy.json", "crawled_articles_BeautifulSoup.json"]
    articles = load_articles(input_files)
    logger.info(f"Total deduplicated articles: {len(articles)}")

    # Load zero-shot classification model
    logger.info("Loading zero-shot classification model (facebook/bart-large-mnli)...")
    classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")

    enriched_articles = []

    for article in tqdm(articles, desc="Classifying Articles"):
        content = article.get("content", "")
        if not content or len(content.strip()) < 50:
            logger.warning(f"Skipping short or empty content for article: {article.get('url')}")
            continue

        # Truncate content to first 2000 chars for performance
        trimmed = content[:2000]

        result = {
            "url": article.get("url"),
            "title": article.get("title"),
            "source": article.get("source"),
            "published": article.get("published"),
            "VT_PrimaryType": classify_article(classifier, trimmed, vt_primary_types),
            "VT_Subtype": classify_article(classifier, trimmed, vt_subtypes),
            "Industry": classify_article(classifier, trimmed, industries),
            "Platform": classify_article(classifier, trimmed, platforms),
            "Severity": classify_article(classifier, trimmed, severities),
            "Actor": classify_article(classifier, trimmed, actors),
            "Compliance": classify_article(classifier, trimmed, compliance_tags),
            "raw_content": trimmed
        }
        enriched_articles.append(result)

    # Save output
    output_file = "classified_articles_ML.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(enriched_articles, f, ensure_ascii=False, indent=4)
    logger.info(f"Saved {len(enriched_articles)} classified articles to {output_file}")

# === 5. Entry point ===
if __name__ == "__main__":
    aggregate_and_classify()
