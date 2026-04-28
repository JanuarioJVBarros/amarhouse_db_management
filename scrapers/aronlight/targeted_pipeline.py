import argparse
import json
import logging
from pathlib import Path

import requests

from beevo.client import BeevoClient
from beevo.config.env_loader import load_environment
from core.publisher import ProductPublisher

from .crawler import AronlightCrawler
from .extractor import AronlightExtractor
from .urls import TARGET_PRODUCT_URLS

logger = logging.getLogger(__name__)


def _normalize_url(url):
    return (url or "").split("#", 1)[0].split("?", 1)[0].rstrip("/") + "/"


def _collect_baseline_urls(products):
    return {
        _normalize_url(product.get("source_url"))
        for product in products or []
        if product.get("source_url")
    }


def _collect_baseline_skus(products):
    skus = set()
    for product in products or []:
        sku = product.get("sku")
        if sku:
            skus.add(str(sku).strip().upper())
        for variant in product.get("variants") or []:
            vsku = variant.get("sku")
            if vsku:
                skus.add(str(vsku).strip().upper())
    return skus


def load_baseline_products(path):
    if not path:
        return []

    baseline_path = Path(path)
    if not baseline_path.exists():
        return []

    return json.loads(baseline_path.read_text(encoding="utf-8"))


def scrape_target_urls(urls, crawler=None, extractor=None):
    crawler = crawler or AronlightCrawler()
    extractor = extractor or AronlightExtractor()

    scraped_products = []
    for index, url in enumerate(urls, start=1):
        logger.info("[aronlight-targeted] [%s/%s] Scraping %s", index, len(urls), url)
        try:
            html = crawler.fetch(url)
        except requests.RequestException as exc:
            logger.warning("[aronlight-targeted] [SKIP] Failed to fetch %s: %s", url, exc)
            continue
        product = extractor.extract(html, url)
        if product is None:
            logger.warning("[aronlight-targeted] No product extracted from %s", url)
            continue
        scraped_products.append(product)

    return scraped_products


def compare_products(scraped_products, baseline_products):
    baseline_urls = _collect_baseline_urls(baseline_products)
    baseline_skus = _collect_baseline_skus(baseline_products)
    missing = []
    matched = []

    for product in scraped_products:
        source_url = _normalize_url(getattr(product, "source_url", None))
        product_skus = set()

        if getattr(product, "sku", None):
            product_skus.add(str(product.sku).strip().upper())

        for variant in getattr(product, "variants", []) or []:
            sku = variant.get("sku")
            if sku:
                product_skus.add(str(sku).strip().upper())

        in_baseline = source_url in baseline_urls or bool(product_skus & baseline_skus)
        target = matched if in_baseline else missing
        target.append(product)

    return {"matched": matched, "missing": missing}


def save_products(path, products):
    serializable = [product.__dict__ if hasattr(product, "__dict__") else product for product in products]
    Path(path).write_text(json.dumps(serializable, ensure_ascii=False, indent=2), encoding="utf-8")


def publish_products(products, dry_run=False):
    if dry_run:
        return [{"product_id": product.slug, "status": "dry-run"} for product in products]

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
        logger.info("[aronlight-targeted] Publishing %s", product.slug)
        result = publisher.publish(product)
        if result:
            results.append(result)

    return results


def main(argv=None):
    cli = argparse.ArgumentParser(
        description="Scrape a curated set of Aronlight product links, compare them against a baseline JSON, and optionally publish missing products.",
    )
    cli.add_argument(
        "--output-file",
        default="aronlight_targeted_preview.json",
        help="JSON output path for the scraped targeted products.",
    )
    cli.add_argument(
        "--baseline-file",
        default="aronlight_preview.json",
        help="Existing scraped JSON to compare against.",
    )
    cli.add_argument(
        "--publish-missing",
        action="store_true",
        help="Publish products that are missing from the baseline file.",
    )
    cli.add_argument(
        "--dry-run",
        action="store_true",
        help="When combined with --publish-missing, report publish candidates without sending them to Beevo.",
    )
    cli.add_argument(
        "--product-url",
        action="append",
        dest="product_urls",
        help="Override the default curated URL list. Can be passed multiple times.",
    )
    args = cli.parse_args(argv)

    logging.basicConfig(level=logging.INFO)

    product_urls = args.product_urls or TARGET_PRODUCT_URLS
    scraped_products = scrape_target_urls(product_urls)
    save_products(args.output_file, scraped_products)

    baseline_products = load_baseline_products(args.baseline_file)
    comparison = compare_products(scraped_products, baseline_products)

    print(f"Scraped {len(scraped_products)} targeted Aronlight products")
    print(f"Matched baseline products: {len(comparison['matched'])}")
    print(f"Missing from baseline: {len(comparison['missing'])}")

    if args.publish_missing:
        publish_results = publish_products(comparison["missing"], dry_run=args.dry_run)
        print(f"Publish candidates processed: {len(publish_results)}")

    return {
        "scraped": len(scraped_products),
        "matched": len(comparison["matched"]),
        "missing": len(comparison["missing"]),
        "output_file": args.output_file,
    }


if __name__ == "__main__":
    main()
