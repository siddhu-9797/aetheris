import os
import django
import logging
import sys


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aetheris_core.settings")

django.setup()

from vtagent.models import RawArticle, ClassifiedArticle

from transformers import pipeline

classifier = pipeline("zero-shot-classification", model="MoritzLaurer/deberta-v3-large-zeroshot-v1")
print("Model loaded and ready!")


# Setup logging to file
logging.basicConfig(
    filename="classification_log.txt",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

def classify_article(classifier, text):
    field_labels = {
        "VT_PrimaryType": ["threat", "vulnerability", "cyber attack", "compliance", "ransomware", "data breach"],
        "VT_Subtype": ["phishing", "malware", "ddos", "sql injection", "brute force", "ransomware"],
        "Industry": ["finance", "healthcare", "education", "government", "energy", "defense"],
        "Platform": ["email", "google drive", "onedrive", "dropbox", "windows", "linux", "cloud", "android"],
        "Severity": ["critical", "high", "medium", "low"],
        "Impact": ["data theft", "service outage", "data breach", "system takeover"],
        "Actor": ["state-sponsored", "cybercriminal", "hacktivist", "insider"],
        "Origin": ["internal", "external"],
        "Compliance": ["gdpr", "hipaa", "pci-dss", "iso27001"],
    }

    results = {}
    for field, labels in field_labels.items():
        try:
            pred = classifier(text, labels, multi_label=True)
            selected = [label for label, score in zip(pred['labels'], pred['scores']) if score > 0.3]
            results[field] = selected
        except Exception as e:
            logging.error(f"Failed to classify field {field}: {e}")
            results[field] = []
    return results

def main():
    logging.info("Loading Zero-Shot Classification pipeline...")
    classifier = pipeline("zero-shot-classification", model="MoritzLaurer/deberta-v3-large-zeroshot-v1")

    logging.info("Fetching RawArticles...")
    raw_articles = RawArticle.objects.all()
    to_classify = []

    for raw in raw_articles:
        if not ClassifiedArticle.objects.filter(url=raw.url).exists():
            to_classify.append(raw)

    logging.info(f"Total to classify: {len(to_classify)}")

    for raw in to_classify:
        logging.info(f"Classifying: {raw.title}")
        content = raw.content or ""
        labels = classify_article(classifier, content)

        ClassifiedArticle.objects.create(
            url=raw.url,
            title=raw.title,
            source=raw.source.name,
            published=raw.published,
            classification_source="ml",
            VT_PrimaryType=labels["VT_PrimaryType"],
            VT_Subtype=labels["VT_Subtype"],
            Industry=labels["Industry"],
            Platform=labels["Platform"],
            Severity=labels["Severity"],
            Impact=labels["Impact"],
            Actor=labels["Actor"],
            Origin=labels["Origin"],
            Compliance=labels["Compliance"],
            raw_content=content,
        )

        logging.info(f"Classified: {raw.title} -> {labels['VT_PrimaryType']}")

if __name__ == "__main__":
    try:
        main()
        logging.info("All raw articles classified successfully.")
    except Exception as e:
        logging.exception(f"Classification script failed: {e}")
