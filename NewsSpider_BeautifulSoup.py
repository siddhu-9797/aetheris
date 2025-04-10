import requests
import feedparser
from bs4 import BeautifulSoup
import json
from datetime import datetime
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global headers to mimic a browser (default User-Agent)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36"
}

def fetch_full_article(url):
    """
    Attempts to fetch the full article text from a given URL using multiple retries and different User-Agents if a 403 is encountered.
    Returns a tuple (content, errors) where errors is a list of error messages.
    """
    logger.info(f"Fetching full article from: {url}")
    errors = []
    retries = 0
    max_retries = 3
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:88.0) Gecko/20100101 Firefox/88.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.77 Safari/537.36"
    ]
    current_headers = HEADERS.copy()
    while retries < max_retries:
        try:
            response = requests.get(url, headers=current_headers, timeout=10)
            if response.status_code == 403:
                error_msg = f"403 Forbidden encountered on attempt {retries+1} for URL {url}"
                logger.error(error_msg)
                errors.append(error_msg)
                wait_time = 2 ** retries
                time.sleep(wait_time)
                retries += 1
                if retries < len(user_agents):
                    current_headers["User-Agent"] = user_agents[retries]
                continue
            response.raise_for_status()
            break
        except Exception as e:
            error_msg = f"Error fetching URL {url}: {e}"
            logger.error(error_msg)
            errors.append(error_msg)
            return "", errors
    else:
        error_msg = f"Failed to fetch URL {url} after {max_retries} attempts."
        logger.error(error_msg)
        errors.append(error_msg)
        return "", errors

    soup = BeautifulSoup(response.text, "html.parser")
    content = ""
    selectors = [
        {"name": "div", "attrs": {"class": "article-content"}},
        {"name": "div", "attrs": {"class": "entry-content"}},
        {"name": "div", "attrs": {"class": "post-content"}},
        {"name": "article"},
        {"name": "div", "attrs": {"id": "content"}}
    ]
    for sel in selectors:
        container = soup.find(sel["name"], sel.get("attrs", {}))
        if container:
            content = container.get_text(separator="\n", strip=True)
            if content and len(content) > 200:
                break
    if not content:
        paragraphs = soup.find_all("p")
        content = "\n".join([p.get_text(strip=True) for p in paragraphs])
    if len(content) < 200:
        warning_msg = f"Content from {url} is very short and may be incomplete."
        logger.warning(warning_msg)
        errors.append(warning_msg)
    return content, errors

def fetch_from_rss(feed_url, source_name, source_category="Cybersecurity", default_section=""):
    """
    Fetches articles from an RSS feed and returns a list of article dictionaries with extended fields.
    """
    logger.info(f"Fetching RSS feed for {source_name}: {feed_url}")
    articles = []
    try:
        feed = feedparser.parse(feed_url)
    except Exception as e:
        logger.error(f"Error parsing RSS feed {feed_url}: {e}")
        return articles
    for entry in feed.entries:
        url = entry.get("link", "")
        title = entry.get("title", "")
        published = entry.get("published", str(datetime.now()))
        author = entry.get("author", "")
        tags = []
        if "tags" in entry:
            tags = [tag.term for tag in entry.tags if hasattr(tag, "term")]
        # Prefer the category from the entry; otherwise use the provided default.
        section = entry.get("category", default_section)
        content = ""
        errors = []
        if "content" in entry and entry.content:
            content = entry.content[0].value
        if not content or len(content) < 100:
            content, fetch_errors = fetch_full_article(url)
            errors.extend(fetch_errors)
        article = {
            "source": source_name,
            "SourceCategory": source_category,
            "title": title,
            "url": url,
            "published": published,
            "content": content,
            "author": author,
            "tags": tags,
            "section": section,
            "scraped_at": str(datetime.now()),
            "errors": errors
        }
        articles.append(article)
    logger.info(f"Fetched {len(articles)} articles from {source_name} via RSS.")
    return articles

def crawl_ncsc():
    """
    Crawls the NCSC news page directly (for government sites without RSS) and returns a list of article dictionaries.
    """
    source_name = "NCSC"
    source_category = "Government"
    url = "https://www.ncsc.gov.uk/news"
    logger.info(f"Crawling {source_name} directly from {url}")
    articles = []
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
    except Exception as e:
        logger.error(f"Error fetching NCSC news page: {e}")
        return articles
    soup = BeautifulSoup(response.text, "html.parser")
    container = soup.find("div", class_="news-list")
    if container:
        links = container.find_all("a", href=True)
    else:
        links = soup.find_all("a", href=True)
    for link in links:
        article_url = link["href"]
        if not article_url.startswith("http"):
            article_url = "https://www.ncsc.gov.uk" + article_url
        title = link.get_text(strip=True)
        if not title:
            continue
        content, fetch_errors = fetch_full_article(article_url)
        article = {
            "source": source_name,
            "SourceCategory": source_category,
            "title": title,
            "url": article_url,
            "published": str(datetime.now()),
            "content": content,
            "author": "",
            "tags": [],
            "section": "",
            "scraped_at": str(datetime.now()),
            "errors": fetch_errors
        }
        articles.append(article)
    logger.info(f"Fetched {len(articles)} articles from {source_name} by direct crawl.")
    return articles

def main():
    all_articles = []
    # List of RSS sources – some URLs are placeholders and should be updated as needed.
    rss_sources = [
        #{"feed_url": "https://feeds.feedburner.com/TheHackersNews", "source": "The Hacker News", "category": "Cybersecurity", "section": ""},
        {"feed_url": "https://securityaffairs.co/wordpress/feed", "source": "Security Affairs", "category": "Cybersecurity", "section": ""},
        #{"feed_url": "https://www.darkreading.com/rss.xml", "source": "Dark Reading", "category": "Cybersecurity", "section": ""},
        {"feed_url": "https://threatpost.com/feed/", "source": "Threatpost", "category": "Cybersecurity", "section": ""},
        {"feed_url": "https://krebsonsecurity.com/feed/", "source": "Krebs on Security", "category": "Cybersecurity", "section": ""},
        # Additional cybersecurity-focused sources (RSS feed URLs may need to be verified)
        {"feed_url": "https://packetstorm.example.com/rss", "source": "PacketStorm News", "category": "Cybersecurity", "section": ""},
        {"feed_url": "https://cybernews.example.com/rss", "source": "Cybernews", "category": "Cybersecurity", "section": ""},
        {"feed_url": "https://www.csoonline.com/uk/rss", "source": "CSO Online UK", "category": "Cybersecurity", "section": ""},
        {"feed_url": "https://cyberscoop.example.com/rss", "source": "Cyberscoop", "category": "Cybersecurity", "section": ""},
        {"feed_url": "https://www.bleepingcomputer.com/feed/", "source": "Bleeping Computer", "category": "Cybersecurity", "section": ""},
        {"feed_url": "https://www.helpnetsecurity.com/feed/", "source": "Help Net Security", "category": "Cybersecurity", "section": ""},
        {"feed_url": "https://www.infosecurity-magazine.com/rss", "source": "Infosecurity Magazine", "category": "Cybersecurity", "section": ""},
        {"feed_url": "https://www.securitymagazine.com/rss", "source": "Security Magazine", "category": "Cybersecurity", "section": ""},
        {"feed_url": "https://cybersecuritynews.com/feed", "source": "Cybersecurity News", "category": "Cybersecurity", "section": ""},
        {"feed_url": "https://www.cpomagazine.com/feed/", "source": "CPO Magazine", "category": "Cybersecurity", "section": ""},
        {"feed_url": "https://gbhackers.com/feed/", "source": "GBHackers", "category": "Cybersecurity", "section": ""},
        {"feed_url": "https://cybersecurityventures.example.com/rss", "source": "Cybersecurity Ventures", "category": "Cybersecurity", "section": ""},
        {"feed_url": "https://securityledger.example.com/rss", "source": "Security Ledger", "category": "Cybersecurity", "section": ""},
        {"feed_url": "https://www.itsecurityguru.org/rss", "source": "IT Security Guru", "category": "Cybersecurity", "section": ""},
        {"feed_url": "https://www.inforisktoday.com/rss", "source": "Inforisk Today", "category": "Cybersecurity", "section": ""},
        {"feed_url": "https://securelist.com/feed/", "source": "SecureList", "category": "Cybersecurity", "section": ""},
        {"feed_url": "https://www.cybersecurity-insiders.com/feed", "source": "Cybersecurity Insiders", "category": "Cybersecurity", "section": ""},
        # Sites with cybersecurity as a section in overall news sites
        {"feed_url": "https://www.techtarget.com/searchsecurity/feed", "source": "TechTarget SearchSecurity", "category": "Cybersecurity Section", "section": ""},
        {"feed_url": "https://www.forbes.com/cybersecurity/feed", "source": "Forbes Cybersecurity", "category": "Cybersecurity Section", "section": ""},
        {"feed_url": "https://www.theverge.com/cyber-security/rss/index.xml", "source": "The Verge Cyber Security", "category": "Cybersecurity Section", "section": ""},
        {"feed_url": "https://www.infosecinstitute.com/resources/feed", "source": "Infosec Institute Resources", "category": "Cybersecurity Section", "section": ""},
        # News from product vendors
        {"feed_url": "https://www.ibm.com/think/feed/security", "source": "IBM Think Security", "category": "Vendor", "section": ""},
        {"feed_url": "https://news.sophos.com/en-us/category/serious-security/feed/", "source": "Sophos", "category": "Vendor", "section": ""},
        {"feed_url": "https://tripwire.com/state-of-security/feed", "source": "Tripwire State of Security", "category": "Vendor", "section": ""},
        {"feed_url": "https://cyberark.com/resources/blog/feed", "source": "CyberArk Blog", "category": "Vendor", "section": ""},
        # News from research institutes
        {"feed_url": "https://www.sans.org/blog/feed", "source": "SANS Blog", "category": "Research Institute", "section": ""}
    ]
    for src in rss_sources:
        articles = fetch_from_rss(src["feed_url"], src["source"], src["category"], src.get("section", ""))
        all_articles.extend(articles)
    # Add government sites (direct crawl)
    all_articles.extend(crawl_ncsc())
    
    output_file = "crawled_articles_BeautifulSoup.json"
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(all_articles, f, ensure_ascii=False, indent=4)
        logger.info(f"Saved {len(all_articles)} articles to {output_file}.")
    except Exception as e:
        logger.error(f"Error saving articles to file: {e}")

if __name__ == "__main__":
    main()
