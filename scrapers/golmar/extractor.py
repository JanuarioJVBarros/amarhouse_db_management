from urllib.parse import urlparse
from .parser import GolmarParser
from scrapers.base import build_scraped_product


class GolmarExtractor:
    def extract(self, html: str, url: str):
        parser = GolmarParser(html)

        # NAME
        name = parser.text("h1")

        # SLUG
        slug = urlparse(url).path.split("/")[-1]

        # DESCRIPTION (short)
        description = parser.html(".product-info ul")

        # FULL DESCRIPTION
        description_full = parser.html(".product-details-body")

        # PRICE
        price = parser.text(".product-info-price")

        # REFERENCE
        reference = parser.text(".product-info-number")

        # SKU
        sku = parser.text(".product-info-code")

        # IMAGES
        images = parser.images()

        # LABELS (filters sidebar)
        labels = []
        for el in parser.soup.select(".articles-sidebar-selection li"):
            labels.append(el.get_text(" ", strip=True))

        return build_scraped_product(
            name=name,
            slug=slug,
            description=description,
            description_full=description_full,
            price=price,
            reference=reference,
            sku=sku,
            images=images,
            labels=labels,
            source_url=url,
            supplier="golmar",
        )
