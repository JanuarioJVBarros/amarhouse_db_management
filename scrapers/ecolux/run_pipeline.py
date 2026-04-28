import argparse
import logging

from beevo.client import BeevoClient
from beevo.config.env_loader import load_environment
from core.publisher import ProductPublisher
from scrapers.base import SupplierPipeline

from .crawler import EcoluxCrawler
from .extractor import EcoluxExtractor
from .urls import START_URLS

logger = logging.getLogger(__name__)


class EcoluxPipeline(SupplierPipeline):
    def __init__(self, crawler=None, extractor=None, publisher=None):
        super().__init__(
            supplier_name="ecolux",
            crawler=crawler or EcoluxCrawler(),
            extractor=extractor or EcoluxExtractor(),
        )
        self.publisher = publisher

    def publish_missing(self, products, dry_run=False):
        if dry_run:
            logger.info("[ecolux] Dry run enabled: skipping publish for %s product(s)", len(products))
            return [
                {
                    "product_id": product.slug,
                    "status": "dry-run",
                }
                for product in products
            ]

        publisher = self.publisher

        if publisher is None:
            settings = load_environment()
            publisher = ProductPublisher(
                BeevoClient(
                    base_url=settings.beevo_url,
                    beevo_cookie=settings.beevo_cookie,
                    timeout=settings.request_timeout,
                )
            )
        results = []

        for product in products:
            logger.info("[ecolux] Publishing missing product: %s", product.slug)
            result = publisher.publish(product)
            if result:
                results.append(result)

        return results

    def run_and_publish_missing(self, start_urls=None, output_file=None, dry_run=False):
        start_urls = start_urls or START_URLS
        products = super().run(start_urls, output_file=output_file)
        published = self.publish_missing(products, dry_run=dry_run)

        return {
            "scraped": len(products),
            "published": len(published),
            "dry_run": dry_run,
            "products": products,
            "results": published,
        }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    cli = argparse.ArgumentParser(description="Scrape Ecolux products and publish missing ones to Beevo.")
    cli.add_argument(
        "--output-file",
        help="Optional JSON output path for scraped products.",
    )
    cli.add_argument(
        "--dry-run",
        action="store_true",
        help="Scrape and save products but do not publish them to Beevo.",
    )
    cli.add_argument(
        "--start-url",
        action="append",
        dest="start_urls",
        help="Override default start URL(s). Can be passed multiple times.",
    )
    args = cli.parse_args()

    pipeline = EcoluxPipeline()

    result = pipeline.run_and_publish_missing(
        start_urls=args.start_urls or START_URLS,
        output_file=args.output_file,
        dry_run=args.dry_run,
    )

    print(f"Scraped {result['scraped']} Ecolux products")
    if result["dry_run"]:
        print(f"Dry run only. {result['published']} product(s) prepared for publish.")
    else:
        print(f"Published {result['published']} missing Ecolux products")
