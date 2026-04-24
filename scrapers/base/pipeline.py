import json
from datetime import datetime


class SupplierPipeline:
    def __init__(self, supplier_name, crawler, extractor):
        self.supplier_name = supplier_name
        self.crawler = crawler
        self.extractor = extractor

    def scrape(self, start_urls):
        product_urls = []

        for start_url in start_urls:
            product_urls.extend(self.crawler.crawl_category(start_url))

        all_products = []

        for index, url in enumerate(product_urls, start=1):
            print(f"[{self.supplier_name}] [{index}/{len(product_urls)}] Processing: {url}")
            html = self.crawler.fetch(url)
            extracted = self.extractor.extract(html, url)

            if isinstance(extracted, list):
                all_products.extend(extracted)
            elif extracted is not None:
                all_products.append(extracted)

        return all_products

    def save(self, output_file, products):
        serializable = [product.__dict__ if hasattr(product, "__dict__") else product for product in products]
        with open(output_file, "w", encoding="utf-8") as handle:
            json.dump(serializable, handle, ensure_ascii=False, indent=2)

    def default_output_file(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{self.supplier_name}_{timestamp}.json"

    def run(self, start_urls, output_file=None):
        products = self.scrape(start_urls)

        if output_file is None:
            output_file = self.default_output_file()

        self.save(output_file, products)
        return products
