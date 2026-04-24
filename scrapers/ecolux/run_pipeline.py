from scrapers.base import SupplierPipeline

from .crawler import EcoluxCrawler
from .extractor import EcoluxExtractor
from .urls import START_URLS


class EcoluxPipeline(SupplierPipeline):
    def __init__(self, crawler=None, extractor=None):
        super().__init__(
            supplier_name="ecolux",
            crawler=crawler or EcoluxCrawler(),
            extractor=extractor or EcoluxExtractor(),
        )


if __name__ == "__main__":
    pipeline = EcoluxPipeline()
    products = pipeline.run(START_URLS)
    print(f"Extracted {len(products)} Ecolux products")
