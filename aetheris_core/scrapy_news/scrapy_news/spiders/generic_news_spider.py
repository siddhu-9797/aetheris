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

        # Save to DB via thread-safe method with duplicate handling
        try:
            from vtagent.models import NewsSource
            source_obj = NewsSource.objects.get(id=self.source_id)
            
            article_obj, created = await asyncio.to_thread(
                RawArticle.objects.get_or_create,
                url=response.url,
                defaults={
                    'title': article.title or response.url,
                    'source': source_obj,
                    'source_type': "scrapy",
                    'published': str(article.publish_date) if article.publish_date else str(datetime.now()),
                    'content': text,
                    'author': ", ".join(article.authors) if article.authors else "",
                    'tags': [],
                    'section': "",
                    'errors': [],
                    'scraped_at': datetime.now()
                }
            )
            if created:
                self.articles_scraped += 1
                logger.info(f"Saved new article: {article.title}")
        except Exception as e:
            logger.error(f"Error saving article from {response.url}: {e}")

        # Stop early if limit reached
        if self.articles_scraped >= self.max_articles:
            return

        # Follow internal links with filtering
        for href in response.css("a::attr(href)").getall():
            if not href:
                continue
                
            # Filter out unwanted URLs
            invalid_patterns = [
                "javascript:", "mailto:", "tel:", "#", "void(0)",
                "twitter.com", "x.com", "facebook.com", "linkedin.com",
                "about", "contact", "privacy", "/login", "/signup"
            ]
            if any(pattern in href.lower() for pattern in invalid_patterns):
                continue
            
            absolute_url = response.urljoin(href)
            parsed_url = urlparse(absolute_url)
            
            # Only follow same-domain links
            if parsed_url.netloc == self.allowed_domains[0]:
                # Prefer URLs that look like articles
                if any(indicator in absolute_url.lower() for indicator in [
                    "article", "news", "blog", "post", "story", "security", 
                    "hack", "cyber", "threat", "vulnerability", "attack", "breach"
                ]):
                    yield scrapy.Request(absolute_url, callback=self.parse, dont_filter=False)