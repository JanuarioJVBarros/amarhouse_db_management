from scrapers.base import SupplierPipeline

from .crawler import RointeCrawler
from .extractor import RointeExtractor
from .urls import START_URLS


class RointePipeline(SupplierPipeline):
    def __init__(self, crawler=None, extractor=None):
        super().__init__(
            supplier_name="rointe",
            crawler=crawler or RointeCrawler(),
            extractor=extractor or RointeExtractor(),
        )


if __name__ == "__main__":
    pipeline = RointePipeline()
    products = pipeline.run(START_URLS)
    print(f"Extracted {len(products)} Rointe products")
