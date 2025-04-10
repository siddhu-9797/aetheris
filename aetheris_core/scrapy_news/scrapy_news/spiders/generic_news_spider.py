import scrapy
from newspaper import Article
from urllib.parse import urlparse
from datetime import datetime
import logging
import asyncio

from vtagent.models import RawArticle  # Ensure this import is valid

logger = logging.getLogger("generic_news_spider")

class GenericNewsSpider(scrapy.Spider):
    name = "generic_news_spider"

    def __init__(self, source_id=None, start_url=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_urls = [start_url] if start_url else []
        self.source_id = source_id
        self.allowed_domains = [urlparse(start_url).netloc] if start_url else []
        self.max_articles = 50
        self.articles_scraped = 0

    async def parse(self, response):
        if self.articles_scraped >= self.max_articles:
            return

        # Only follow internal links
        if urlparse(response.url).netloc not in self.allowed_domains:
            return

        # Attempt to parse the article
        article = Article(response.url)
        try:
            await asyncio.to_thread(article.download)
            await asyncio.to_thread(article.parse)
        except Exception as e:
            logger.warning(f"Failed to parse article at {response.url}: {e}")
            return

        # Filter out very short or empty content
        text = article.text.strip()
        if not text or len(text) < 100:
            return

        # Save to DB via thread-safe method
        try:
            await asyncio.to_thread(
                RawArticle.objects.create,
                url=response.url,
                title=article.title,
                source=self.allowed_domains[0],
                source_type="scrapy",
                published=datetime.now(),  # Could attempt to parse from article
                content=text,
            )
            self.articles_scraped += 1
        except Exception as e:
            logger.error(f"Error saving article from {response.url}: {e}")

        # Stop early if limit reached
        if self.articles_scraped >= self.max_articles:
            return

        # Follow internal links (no crawling policies applied here — safe to enhance later)
        for href in response.css("a::attr(href)").getall():
            absolute_url = response.urljoin(href)
            if urlparse(absolute_url).netloc == self.allowed_domains[0]:
                yield scrapy.Request(absolute_url, callback=self.parse)