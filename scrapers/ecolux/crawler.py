from scrapers.base import BaseCatalogCrawler

from .parser import EcoluxParser
from .urls import BASE_URL, PRODUCTS_URL


class EcoluxCrawler(BaseCatalogCrawler):
    LANGUAGE_HEADERS = {
        "Accept-Language": "pt-PT,pt;q=0.9,pt-BR;q=0.8,es;q=0.7,en;q=0.6",
    }

    def __init__(
        self,
        base_url=BASE_URL,
        timeout=30,
        session=None,
        original_language="es",
        target_language="pt",
    ):
        super().__init__(base_url=base_url, timeout=timeout, session=session)
        self.original_language = original_language
        self.target_language = target_language
        self._configure_language_preference()

    def _configure_language_preference(self):
        if hasattr(self.session, "headers"):
            self.session.headers.update(self.LANGUAGE_HEADERS)

        googtrans_value = f"/{self.original_language}/{self.target_language}"

        if hasattr(self.session, "cookies"):
            try:
                self.session.cookies.set("googtrans", googtrans_value, path="/")
                self.session.cookies.set("googtrans", googtrans_value)
                self.session.cookies.set("googtrans", googtrans_value, domain="ecolux-lighting.com")
                self.session.cookies.set("gt_auto_switch", "1", path="/")
                self.session.cookies.set("gt_auto_switch", "1", domain="ecolux-lighting.com")
            except Exception:
                pass

    def get_category_links(self, catalog_url=PRODUCTS_URL):
        html = self.fetch(catalog_url)
        parser = EcoluxParser(html)

        links = set()
        for link in parser.all_links(catalog_url):
            if "/categoria_producto/" in link:
                links.add(link.rstrip("/") + "/")
                continue
            if self._is_product_listing_page(link):
                links.add(link.rstrip("/") + "/")

        return sorted(links)

    def _is_product_listing_page(self, link):
        normalized = link.split("?")[0].rstrip("/") + "/"
        return (
            "/productos-ecolux-lighting/" in normalized
            and normalized != PRODUCTS_URL.rstrip("/") + "/"
        )

    def get_product_links(self, category_url):
        html = self.fetch(category_url)
        parser = EcoluxParser(html)

        links = set()
        for link in parser.all_links(category_url):
            if "/productos/" not in link:
                continue
            if "/productos-ecolux-lighting/" in link:
                continue
            links.add(link.split("?")[0].rstrip("/") + "/")

        return sorted(links)

    def crawl_category(self, start_url):
        if "/categoria_producto/" in start_url or self._is_product_listing_page(start_url):
            return self.get_product_links(start_url)

        product_links = []
        for category_url in self.get_category_links(start_url):
            product_links.extend(self.get_product_links(category_url))

        return sorted(set(product_links))
