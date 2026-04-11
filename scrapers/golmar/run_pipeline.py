import json

from .crawler import GolmarCrawler
from .extractor import GolmarExtractor

from core.transformers.golmar_transformer import GolmarTransformer
from core.publisher import ProductPublisher

from beevo.client import BeevoClient

class GolmarPipeline:

    def __init__(self):
        self.crawler = GolmarCrawler()
        self.extractor = GolmarExtractor()
        self.transformer = GolmarTransformer()

        client = BeevoClient()
        self.publisher = ProductPublisher(client)

    # ---------------------------------------------------
    # STEP 1 — SCRAPE
    # ---------------------------------------------------

    def scrape(self, start_url: str):
        print("\n[PIPELINE] Starting crawl...\n")

        product_urls = self.crawler.crawl_category(start_url)

        print(f"\n[PIPELINE] Found {len(product_urls)} products\n")

        products = []

        for url in product_urls:
            html = self.crawler.fetch(url)
            if not html:
                continue

            scraped = self.extractor.extract(html, url)
            products.append(scraped)

        print(f"\n[PIPELINE] Extracted {len(products)} raw products\n")

        return products

    # ---------------------------------------------------
    # STEP 2 — TRANSFORM
    # ---------------------------------------------------

    def transform(self, scraped_products):
        print("\n[PIPELINE] Transforming products...\n")

        transformed = []

        for p in scraped_products:
            try:
                product = self.transformer.transform(p)
                transformed.append(product)
            except Exception as e:
                print(f"[TRANSFORM ERROR] {p.source_url}: {e}")

        print(f"\n[PIPELINE] Transformed {len(transformed)} products\n")

        return transformed

    # ---------------------------------------------------
    # STEP 3 — PUBLISH
    # ---------------------------------------------------

    def publish(self, products):
        print("\n[PIPELINE] Publishing to Beevo...\n")

        results = []

        for product in products:
            try:
                result = self.publisher.publish(product)
                results.append(result)
            except Exception as e:
                print(f"[PUBLISH ERROR] {product.slug}: {e}")

        print(f"\n[PIPELINE] Published {len(results)} products\n")

        return results

    # ---------------------------------------------------
    # FULL PIPELINE
    # ---------------------------------------------------

    def run(self, start_url: str, save_raw=True, save_transformed=True):
        scraped = self.scrape(start_url)
        transformed = self.transform(scraped)
        published = self.publish(transformed)

        # OPTIONAL DEBUG OUTPUT
        if save_raw:
            with open("scraped_products.json", "w", encoding="utf-8") as f:
                json.dump([p.__dict__ for p in scraped], f, indent=2, ensure_ascii=False)

        if save_transformed:
            with open("transformed_products.json", "w", encoding="utf-8") as f:
                json.dump([p.__dict__ for p in transformed], f, indent=2, ensure_ascii=False)

        return {
            "scraped": len(scraped),
            "transformed": len(transformed),
            "published": len(published)
        }


# ---------------------------------------------------
# CLI ENTRY POINT
# ---------------------------------------------------

if __name__ == "__main__":
    pipeline = GolmarPipeline()

    result = pipeline.run(
        start_url="https://www.golmar.es/products/intercom-en"
    )

    print("\n=== PIPELINE RESULT ===")
    print(result)