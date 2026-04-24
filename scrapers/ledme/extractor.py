from scrapers.base import BaseProductExtractor, build_scraped_product

from .parser import LedmeParser


class LedmeExtractor(BaseProductExtractor):
    def extract(self, html, url):
        parser = LedmeParser(html)
        name = parser.text("h1")

        if not name:
            return None

        return build_scraped_product(
            name=name,
            description=parser.html(".product-description"),
            sku=parser.text(".sku"),
            images=[],
            labels=["ledme"],
            source_url=url,
        )
