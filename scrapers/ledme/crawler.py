from scrapers.base import BaseCatalogCrawler

from .urls import BASE_URL


class LedmeCrawler(BaseCatalogCrawler):
    def __init__(self, base_url=BASE_URL, timeout=30, session=None):
        super().__init__(base_url=base_url, timeout=timeout, session=session)

    def crawl_category(self, start_url):
        # TODO: implement category traversal for Ledme.
        return []
