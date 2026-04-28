import re
from collections import deque
from urllib.parse import urlparse

from scrapers.base import BaseCatalogCrawler

from .parser import AronlightParser
from .urls import BASE_URL


class AronlightCrawler(BaseCatalogCrawler):
    LANGUAGE_HEADERS = {
        "Accept-Language": "pt-PT,pt;q=0.9,en;q=0.6,es;q=0.4",
    }

    def __init__(self, base_url=BASE_URL, timeout=30, session=None):
        super().__init__(base_url=base_url, timeout=timeout, session=session)
        if hasattr(self.session, "headers"):
            self.session.headers.update(self.LANGUAGE_HEADERS)

    def _normalize_url(self, url):
        return url.split("#", 1)[0].split("?", 1)[0].rstrip("/") + "/"

    def _localize_url(self, url):
        normalized = self._normalize_url(url)
        # Aronlight mixes Portuguese and English links inside the same site map.
        # Normalizing to the Portuguese root keeps the scraper aligned with the
        # content version we want to publish into Beevo.
        return normalized.replace("/en/", "/", 1)

    def _category_root(self, url):
        normalized = self._normalize_url(url)
        return re.sub(r"/page/\d+/$", "/", normalized)

    def _is_product_link(self, url):
        return "/project-details/" in url

    def _is_category_pagination_link(self, url, category_root):
        normalized = self._normalize_url(url)
        if self._is_product_link(normalized):
            return False
        if normalized == category_root:
            return True
        return normalized.startswith(category_root) and "/page/" in normalized

    def crawl_category(self, start_url):
        queue = deque([self._localize_url(start_url)])
        visited = set()
        product_links = set()
        category_root = self._category_root(start_url)

        while queue:
            current_url = queue.popleft()
            if current_url in visited:
                continue

            visited.add(current_url)
            html = self.fetch(current_url)
            parser = AronlightParser(html)

            for link in parser.all_links(current_url):
                normalized = self._localize_url(link)

                if self._is_product_link(normalized):
                    product_links.add(normalized)
                    continue

                parsed = urlparse(normalized)
                if parsed.netloc and parsed.netloc != urlparse(self.base_url).netloc:
                    continue

                if self._is_category_pagination_link(normalized, category_root) and normalized not in visited:
                    # Category pages frequently paginate but product pages do
                    # not, so we only keep following links that stay inside the
                    # same catalog branch.
                    queue.append(normalized)

        return sorted(product_links)
