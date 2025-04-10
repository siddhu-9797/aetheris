import scrapy
from scrapy import Request
from scrapy.crawler import CrawlerProcess
from datetime import datetime
import time
import re
import logging

logger = logging.getLogger(__name__)

class NewsSpider(scrapy.Spider):
    name = "news_spider"
    handle_httpstatus_list = [403, 429]
    MAX_ARTICLES_PER_SOURCE = 50
    article_counts = {}

    sources = [
        {"url": "https://thehackernews.com", "source": "The Hacker News", "category": "Cybersecurity", "section": ""},
        #{"url": "https://securityaffairs.com", "source": "Security Affairs", "category": "Cybersecurity", "section": ""},
        {"url": "https://www.darkreading.com", "source": "Dark Reading", "category": "Cybersecurity", "section": ""},
        {"url": "https://threatpost.com", "source": "Threatpost", "category": "Cybersecurity", "section": ""},
        {"url": "https://krebsonsecurity.com", "source": "Krebs on Security", "category": "Cybersecurity", "section": ""},
        {"url": "https://packetstorm.news", "source": "PacketStorm News", "category": "Cybersecurity", "section": ""},
        {"url": "https://cybernews.com", "source": "Cybernews", "category": "Cybersecurity", "section": ""},
        {"url": "https://www.csoonline.com/uk/", "source": "CSO Online UK", "category": "Cybersecurity", "section": ""},
        {"url": "https://cyberscoop.com", "source": "Cyberscoop", "category": "Cybersecurity", "section": ""},
        {"url": "https://www.bleepingcomputer.com", "source": "Bleeping Computer", "category": "Cybersecurity", "section": ""},
        {"url": "https://www.helpnetsecurity.com", "source": "Help Net Security", "category": "Cybersecurity", "section": ""},
        {"url": "https://www.infosecurity-magazine.com", "source": "Infosecurity Magazine", "category": "Cybersecurity", "section": ""},
        {"url": "https://www.securitymagazine.com", "source": "Security Magazine", "category": "Cybersecurity", "section": ""},
        {"url": "https://cybersecuritynews.com", "source": "Cybersecurity News", "category": "Cybersecurity", "section": ""},
        {"url": "https://www.cpomagazine.com", "source": "CPO Magazine", "category": "Cybersecurity", "section": ""},
        {"url": "https://gbhackers.com", "source": "GBHackers", "category": "Cybersecurity", "section": ""},
        {"url": "https://cybersecurityventures.com", "source": "Cybersecurity Ventures", "category": "Cybersecurity", "section": ""},
        {"url": "https://securityledger.com", "source": "Security Ledger", "category": "Cybersecurity", "section": ""},
        {"url": "https://www.itsecurityguru.org", "source": "IT Security Guru", "category": "Cybersecurity", "section": ""},
        {"url": "https://www.inforisktoday.com", "source": "Inforisk Today", "category": "Cybersecurity", "section": ""},
        {"url": "https://securelist.com", "source": "SecureList", "category": "Cybersecurity", "section": ""},
        {"url": "https://www.cybersecurity-insiders.com", "source": "Cybersecurity Insiders", "category": "Cybersecurity", "section": ""},
        # You can add more...
    ]

    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:88.0) Gecko/20100101 Firefox/88.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.77 Safari/537.36"
    ]
    max_retries = 3

    def clean_content(self, text):
        if not text:
            return ""
        text = re.sub(r'[\r\n\t]+', ' ', text)
        text = re.sub(r'\s{2,}', ' ', text)
        text = re.sub(r'initializeOnLoaded\s*\(.*?\}\);?', '', text, flags=re.DOTALL)
        text = re.sub(r'jQuery\(.*?\}\);?', '', text, flags=re.DOTALL)
        text = re.sub(r'<script.*?>.*?</script>', '', text, flags=re.DOTALL)
        text = re.sub(r'<style.*?>.*?</style>', '', text, flags=re.DOTALL)
        text = re.sub(r'\.[\w\-]+[\s]*\{[^}]*\}', '', text)  # CSS .class {...}
        text = re.sub(r'\#[\w\-]+[\s]*\{[^}]*\}', '', text)  # CSS #id {...}
        text = re.sub(r'\{[^{}]*\}', '', text)  # remaining {...}
        return text.strip()

    def start_requests(self):
        for src in self.sources:
            self.article_counts[src["source"]] = 0
            yield Request(
                url=src["url"],
                callback=self.parse,
                meta={"source_info": src, "retry_count": 0, "errors": []},
                headers={"User-Agent": self.user_agents[0]},
                dont_filter=True
            )

    def parse(self, response):
        source_info = response.meta["source_info"]
        source_key = source_info["source"]

        if self.article_counts[source_key] >= self.MAX_ARTICLES_PER_SOURCE:
            return

        links = response.css("a::attr(href)").getall()
        for link in links:
            if not link.startswith("http"):
                link = response.urljoin(link)
            if source_info["url"] in link:
                if self.article_counts[source_key] < self.MAX_ARTICLES_PER_SOURCE:
                    yield Request(
                        url=link,
                        callback=self.parse_article,
                        meta=response.meta.copy(),
                        headers={"User-Agent": self.user_agents[0]},
                        dont_filter=True
                    )

    def parse_article(self, response):
        meta = response.meta
        source_info = meta["source_info"]
        source_key = source_info["source"]

        if self.article_counts[source_key] >= self.MAX_ARTICLES_PER_SOURCE:
            return

        retry_count = meta.get("retry_count", 0)
        errors = meta.get("errors", [])

        if response.status in [403, 429]:
            code = response.status
            error_msg = f"{code} error on {response.url}"
            errors.append(error_msg)
            if retry_count < self.max_retries:
                wait_time = 2 ** retry_count
                new_headers = {"User-Agent": self.user_agents[retry_count % len(self.user_agents)]}
                self.logger.warning(f"{error_msg}. Retrying in {wait_time}s")
                time.sleep(wait_time)
                meta.update({"retry_count": retry_count + 1, "errors": errors})
                yield Request(
                    url=response.url,
                    callback=self.parse_article,
                    meta=meta,
                    headers=new_headers,
                    dont_filter=True
                )
            return

        title = response.css("h1::text").get() or response.xpath("//title/text()").get()
        title = title.strip() if title else ""

        content = ""
        for sel in ["div.article-content", "div.entry-content", "div.post-content", "article", "div#content"]:
            raw_text = response.css(sel).xpath("string()").get()
            if raw_text and len(raw_text.strip()) > 200:
                content = self.clean_content(raw_text)
                break
        if not content:
            fallback = " ".join(response.css("p::text").getall()).strip()
            content = self.clean_content(fallback)

        published = (response.css("meta[property='article:published_time']::attr(content)").get() or
                     response.css("meta[name='pubdate']::attr(content)").get() or
                     str(datetime.now()))
        author = response.css("meta[name='author']::attr(content)").get() or ""
        tags = response.css("meta[property='article:tag']::attr(content)").getall()
        section = response.css("meta[property='article:section']::attr(content)").get() or source_info.get("section", "")

        item = {
            "source": source_key,
            "SourceCategory": source_info.get("category", ""),
            "title": title,
            "url": response.url,
            "published": published,
            "content": content,
            "author": author,
            "tags": tags,
            "section": section,
            "scraped_at": str(datetime.now()),
            "errors": errors
        }

        self.article_counts[source_key] += 1
        yield item

if __name__ == "__main__":
    process = CrawlerProcess(settings={
        "FEEDS": {
            "crawled_articles_Scrapy.json": {
                "format": "json",
                "encoding": "utf8",
                "indent": 4
            }
        },
        "LOG_LEVEL": "INFO"
    })
    process.crawl(NewsSpider)
    process.start()
