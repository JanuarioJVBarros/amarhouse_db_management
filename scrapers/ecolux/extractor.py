from scrapers.base import BaseProductExtractor, build_scraped_product

from .parser import EcoluxParser


class EcoluxExtractor(BaseProductExtractor):
    def extract(self, html, url):
        parser = EcoluxParser(html)
        name = parser.text("h1")

        if not name:
            return None

        return build_scraped_product(
            name=name,
            description=parser.html(".product-description"),
            sku=parser.text(".sku"),
            images=[],
            labels=["ecolux"],
            source_url=url,
        )
