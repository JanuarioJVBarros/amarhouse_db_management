from scrapers.base import SupplierPipeline

from .crawler import GolmarCrawler
from .extractor import GolmarExtractor
from .urls import START_URLS


class GolmarPipeline(SupplierPipeline):
    def __init__(self, crawler=None, extractor=None):
        super().__init__(
            supplier_name="golmar",
            crawler=crawler or GolmarCrawler(),
            extractor=extractor or GolmarExtractor(),
        )


if __name__ == "__main__":
    pipeline = GolmarPipeline()
    products = pipeline.run(START_URLS)
    print(f"Extracted {len(products)} Golmar products")
