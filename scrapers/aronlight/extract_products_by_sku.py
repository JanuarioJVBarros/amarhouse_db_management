import argparse
import json
import logging
from pathlib import Path

from scrapers.base import SupplierPipeline

from .crawler import AronlightCrawler
from .extractor import AronlightExtractor
from .urls import SKU_START_URLS

logger = logging.getLogger(__name__)


DEFAULT_SKUS = [
    "ILAR-01013",
    "ILAR-01014",
    "ILAR-02538",
    "ILAR-02539",
    "ILAR-02540",
    "ILAR-02541",
    "ILAR-02952",
    "ILAR-02953",
    "ILAR-02164",
    "ILAR-02719",
    "ILAR-02718",
    "ILAR-02717",
    "ILAR-02885",
    "ILDV-00044",
    "ILDV-01139",
    "ILDV-00045",
    "ILAR-01447",
    "ILAR-02608",
    "ILAR-01993",
    "ILAR-02609",
    "ILAR-01615",
    "ILAR-02610",
    "ILAR-03010",
    "ILAR-01900",
    "ILAR-01901",
    "ILAR-02021",
    "ILAR-01904",
    "ILAR-01905",
    "ILAR-03013",
    "ILAR-03014",
]


def normalize_sku(value):
    return str(value or "").strip().upper()


def load_skus(path=None):
    if not path:
        return DEFAULT_SKUS

    lines = Path(path).read_text(encoding="utf-8").splitlines()
    skus = []
    for line in lines:
        normalized = normalize_sku(line)
        if normalized:
            skus.append(normalized)
    return skus


def product_skus(product):
    skus = set()
    if getattr(product, "sku", None):
        skus.add(normalize_sku(product.sku))
    for variant in getattr(product, "variants", []) or []:
        sku = variant.get("sku")
        if sku:
            skus.add(normalize_sku(sku))
    return {sku for sku in skus if sku}


def filter_products_by_skus(products, wanted_skus):
    wanted = {normalize_sku(sku) for sku in wanted_skus if normalize_sku(sku)}
    matched_products = []
    found_skus = set()

    for product in products:
        skus = product_skus(product)
        if not (skus & wanted):
            continue
        matched_products.append(product)
        found_skus.update(skus & wanted)

    missing_skus = sorted(wanted - found_skus)
    return {
        "matched_products": matched_products,
        "found_skus": sorted(found_skus),
        "missing_skus": missing_skus,
    }


def save_json(path, payload):
    Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def serializable_products(products):
    return [product.__dict__ if hasattr(product, "__dict__") else product for product in products]


def main(argv=None):
    cli = argparse.ArgumentParser(
        description="Scrape Aronlight and extract only products containing a target SKU list.",
    )
    cli.add_argument(
        "--sku-file",
        help="Optional text file with one SKU per line. Defaults to the built-in driver SKU list.",
    )
    cli.add_argument(
        "--output-file",
        default="aronlight_sku_matches.json",
        help="JSON output path for matched products.",
    )
    cli.add_argument(
        "--report-file",
        default="aronlight_sku_report.json",
        help="JSON output path for the found/missing SKU report.",
    )
    cli.add_argument(
        "--start-url",
        action="append",
        dest="start_urls",
        help="Override default start URL(s). Can be passed multiple times.",
    )
    cli.add_argument(
        "--product-url",
        action="append",
        dest="product_urls",
        help="Optional direct product URL(s) to scrape in addition to category crawling.",
    )
    args = cli.parse_args(argv)

    logging.basicConfig(level=logging.INFO)

    crawler = AronlightCrawler()
    extractor = AronlightExtractor()
    pipeline = SupplierPipeline("aronlight-sku", crawler, extractor)

    urls = args.start_urls or SKU_START_URLS
    products = pipeline.scrape(urls)

    for direct_url in args.product_urls or []:
        logger.info("[aronlight-sku] Scraping direct product %s", direct_url)
        html = crawler.fetch(direct_url)
        product = extractor.extract(html, direct_url)
        if product is not None:
            products.append(product)

    result = filter_products_by_skus(products, load_skus(args.sku_file))

    save_json(args.output_file, serializable_products(result["matched_products"]))
    save_json(
        args.report_file,
        {
            "found_skus": result["found_skus"],
            "missing_skus": result["missing_skus"],
            "matched_product_count": len(result["matched_products"]),
        },
    )

    print(f"Matched products: {len(result['matched_products'])}")
    print(f"Found SKUs: {len(result['found_skus'])}")
    print(f"Missing SKUs: {len(result['missing_skus'])}")
    return result


if __name__ == "__main__":
    main()
