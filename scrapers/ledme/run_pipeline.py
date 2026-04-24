from scrapers.base import SupplierPipeline

from .crawler import LedmeCrawler
from .extractor import LedmeExtractor
from .urls import START_URLS


class LedmePipeline(SupplierPipeline):
    def __init__(self, crawler=None, extractor=None):
        super().__init__(
            supplier_name="ledme",
            crawler=crawler or LedmeCrawler(),
            extractor=extractor or LedmeExtractor(),
        )


if __name__ == "__main__":
    pipeline = LedmePipeline()
    products = pipeline.run(START_URLS)
    print(f"Extracted {len(products)} Ledme products")
