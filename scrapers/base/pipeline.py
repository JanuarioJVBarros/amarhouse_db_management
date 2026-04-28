import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class SupplierPipeline:
    def __init__(self, supplier_name, crawler, extractor):
        self.supplier_name = supplier_name
        self.crawler = crawler
        self.extractor = extractor

    def scrape(self, start_urls):
        logger.info("[%s] Starting scrape for %s start url(s)", self.supplier_name, len(start_urls))
        product_urls = []

        for start_url in start_urls:
            logger.info("[%s] Discovering product URLs from %s", self.supplier_name, start_url)
            discovered_urls = self.crawler.crawl_category(start_url)
            logger.info("[%s] Found %s product URL(s) from %s", self.supplier_name, len(discovered_urls), start_url)
            product_urls.extend(discovered_urls)

        product_urls = sorted(set(product_urls))
        logger.info("[%s] Total unique product URLs: %s", self.supplier_name, len(product_urls))

        all_products = []

        for index, url in enumerate(product_urls, start=1):
            logger.info("[%s] [%s/%s] Processing %s", self.supplier_name, index, len(product_urls), url)
            html = self.crawler.fetch(url)
            if not html:
                logger.warning("[%s] Empty response for %s", self.supplier_name, url)
                continue
            extracted = self.extractor.extract(html, url)

            if isinstance(extracted, list):
                all_products.extend(extracted)
            elif extracted is not None:
                all_products.append(extracted)
            else:
                logger.warning("[%s] Extractor returned no product for %s", self.supplier_name, url)

        logger.info("[%s] Total extracted products: %s", self.supplier_name, len(all_products))

        return all_products

    def save(self, output_file, products):
        serializable = [product.__dict__ if hasattr(product, "__dict__") else product for product in products]
        with open(output_file, "w", encoding="utf-8") as handle:
            json.dump(serializable, handle, ensure_ascii=False, indent=2)
        logger.info("[%s] Saved %s product(s) to %s", self.supplier_name, len(products), output_file)

    def default_output_file(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{self.supplier_name}_{timestamp}.json"

    def run(self, start_urls, output_file=None):
        products = self.scrape(start_urls)

        if output_file is None:
            output_file = self.default_output_file()

        self.save(output_file, products)
        return products
