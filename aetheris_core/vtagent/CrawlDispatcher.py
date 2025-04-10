# CrawlDispatcher.py
import os
import re
import time
import json
import logging
import subprocess
import requests
from bs4 import BeautifulSoup
from newspaper import Article
from fake_useragent import UserAgent
from datetime import datetime
from vtagent.models import RawArticle

logger = logging.getLogger(__name__)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ua = UserAgent()
HEADERS = {
    "User-Agent": ua.random,
    "Accept-Language": "en-GB,en;q=0.9",
    "Referer": "https://www.google.com",
    "DNT": "1"
}

def run_scrapy(source):
    try:
        result = subprocess.run(
            [
                "scrapy", "crawl", "generic_news_spider",
                "-a", f"start_url={source.url}",
                "-a", f"source_id={source.id}"
            ],
            cwd=os.path.join(BASE_DIR, "scrapy_news"),
            capture_output=True,
            text=True,
            timeout=300
        )
        logger.info(result.stdout)
        logger.error(result.stderr)
        if result.returncode != 0:
            return 0, f"Scrapy crawl failed: {result.stderr.strip()}"
    except Exception as e:
        return 0, str(e)
    return 0, None  # Scrapy handles DB insertion directly

def run_bs4(source):
    errors = []
    count = 0
    seen_urls = set()
    try:
        response = requests.get(source.url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        links = [a.get("href") for a in soup.find_all("a", href=True)]
        for url in links:
            if count >= 50:
                break
            if not url or url in seen_urls:
                continue
            if any(x in url.lower() for x in ["about", "contact", "privacy", "/login", "/signup"]):
                continue
            full_url = url if url.startswith("http") else requests.compat.urljoin(source.url, url)
            seen_urls.add(full_url)
            try:
                article = Article(full_url)
                article.download()
                article.parse()
                text = article.text.strip()
                if not text or len(text) < 300:
                    # fallback if newspaper3k fails
                    fallback_resp = requests.get(full_url, headers=HEADERS, timeout=10)
                    fallback_soup = BeautifulSoup(fallback_resp.text, "html.parser")
                    text = fallback_soup.get_text(strip=True, separator="\n")
                if text and len(text) >= 300:
                    RawArticle.objects.create(
                        source=source,
                        source_type="bs4",
                        title=article.title or full_url,
                        url=full_url,
                        published=str(article.publish_date) if article.publish_date else str(datetime.now()),
                        content=text,
                        author=", ".join(article.authors) if article.authors else "",
                        tags=[],
                        section="",
                        errors=[],
                        scraped_at=datetime.now()
                    )
                    count += 1
            except Exception as e:
                logger.warning(f"Failed to extract article using newspaper3k: {e} on URL {full_url}")
                errors.append(str(e))
    except Exception as e:
        logger.error(f"BS4 failed for {source.url}: {e}")
        errors.append(str(e))
    return count, errors

def crawl_news_source(source, use_scrapy=False, use_bs4=False):
    total = 0
    errors = []
    if use_scrapy:
        _, err = run_scrapy(source)
        if err:
            errors.append(err)
    if use_bs4:
        c, err = run_bs4(source)
        total += c
        if err:
            errors.extend(err if isinstance(err, list) else [err])
    return total, errors
