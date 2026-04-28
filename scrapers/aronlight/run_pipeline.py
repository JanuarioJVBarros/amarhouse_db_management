import argparse
import logging

from scrapers.base import SupplierPipeline

from .crawler import AronlightCrawler
from .extractor import AronlightExtractor
from .urls import START_URLS


class AronlightPipeline(SupplierPipeline):
    def __init__(self, crawler=None, extractor=None):
        super().__init__(
            supplier_name="aronlight",
            crawler=crawler or AronlightCrawler(),
            extractor=extractor or AronlightExtractor(),
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    cli = argparse.ArgumentParser(description="Scrape Aronlight products.")
    cli.add_argument("--output-file", help="Optional JSON output path for scraped products.")
    cli.add_argument(
        "--start-url",
        action="append",
        dest="start_urls",
        help="Override default start URL(s). Can be passed multiple times.",
    )
    args = cli.parse_args()

    pipeline = AronlightPipeline()
    products = pipeline.run(args.start_urls or START_URLS, output_file=args.output_file)
    print(f"Extracted {len(products)} Aronlight products")
