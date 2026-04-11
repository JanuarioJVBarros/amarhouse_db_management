import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re

from .urls import BASE_URL

class GolmarCrawler:

    def __init__(self, delay=0.4):
        self.delay = delay

        self.visited = set()
        self.product_urls = set()

        # IMPORTANT: restrict crawl to golmar only
        self.allowed_domain = "golmar.es"

    # ---------------------------------------------------
    # FETCH (offline-safe optional hook stays compatible)
    # ---------------------------------------------------

    def fetch(self, url: str):
        if url in self.visited:
            return None

        self.visited.add(url)

        try:
            print(f"[FETCH] {url}")
            r = requests.get(url, timeout=15)
            time.sleep(self.delay)

            if r.status_code != 200:
                return None

            return r.text

        except Exception as e:
            print(f"[ERROR] {url}: {e}")
            return None

    # ---------------------------------------------------
    # URL CLASSIFICATION
    # ---------------------------------------------------
    
    def is_product_url(self, url: str) -> bool:
        """
        Real product pages in Golmar:
        /products/<slug>
        but NOT /products listing page itself
        """
        parsed = urlparse(url)

        if self.allowed_domain not in parsed.netloc:
            return False

        path = parsed.path.strip("/").split("/")

        # must start with products
        if len(path) < 2:
            return False

        if path[0] != "products":
            return False
        
        # edge case
        if 'intercom-en' in path:
            return False
        
        # product pages have slug after /products/
        return len(path) == 2

    def is_category_url(self, url: str) -> bool:
        parsed = urlparse(url)

        if self.allowed_domain not in parsed.netloc:
            return False

        path = parsed.path.strip("/").split("/")

        # category listing pages
        if len(path) == 1 and path[0] == "products":
            return True

        return False

    def is_valid_internal_link(self, url: str) -> bool:
        return self.allowed_domain in urlparse(url).netloc

    # ---------------------------------------------------
    # LINK EXTRACTION
    # ---------------------------------------------------

    def extract_links(self, html: str, base_url: str):
        soup = BeautifulSoup(html, "html.parser")

        links = set()

        for a in soup.find_all("a", href=True):
            url = urljoin(base_url, a["href"])

            if self.is_valid_internal_link(url):
                links.add(url)

        return links

    # ---------------------------------------------------
    # MAIN CRAWL (FIXED LOGIC)
    # ---------------------------------------------------
    def crawl_category(self, start_url: str):
        page = 1

        while True:
            url = start_url if page == 1 else f"{start_url}/{page}"

            html = self.fetch(url)
            if not html:
                break

            links = self.extract_links(html, url)
            product_found = False

            for link in links:
                if self.is_product_url(link):
                    self.product_urls.add(link)
                    product_found = True

            if not product_found:
                break

            page += 1

        return sorted(self.product_urls)
