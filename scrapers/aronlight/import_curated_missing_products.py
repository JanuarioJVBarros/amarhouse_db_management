import argparse
import json
import logging
from pathlib import Path

from beevo.client import BeevoClient
from beevo.config.env_loader import load_environment
from core.publisher import ProductPublisher
from scrapers.base import SupplierPipeline

from .crawler import AronlightCrawler
from .extractor import AronlightExtractor
from .urls import BASE_URL, SKU_START_URLS

logger = logging.getLogger(__name__)


CURATED_TARGETS = [
    {
        "name": "MODULE EYE ZOOM",
        "expected_skus": ["ILAR-02964", "ILAR-02837"],
        "source_urls": [f"{BASE_URL}/en/project-details/eye/"],
    },
    {
        "name": "GLAZ",
        "expected_skus": ["ILAR-02239", "ILAR-02240"],
        "source_urls": [],
    },
    {
        "name": "BACKLIT 600X600",
        "expected_skus": ["ILAR-02914", "ILAR-03597", "ILAR-03611"],
        "source_urls": [
            f"{BASE_URL}/project-details/led-panel-backlit/",
            f"{BASE_URL}/project-details/aron-painel-backlit-60x60/",
            f"{BASE_URL}/project-details/painel-backlit-24w-60x60/",
            f"{BASE_URL}/project-details/painel-backlit-40w-60x60/",
            f"{BASE_URL}/project-details/painel-backlit-40w-60x60-ugr/",
        ],
    },
    {
        "name": "BACKLIT 1200X300",
        "expected_skus": ["ILAR-02979", "ILAR-02161"],
        "source_urls": [
            f"{BASE_URL}/project-details/led-panel-backlit/",
            f"{BASE_URL}/project-details/painel-edgelit-35w-120x30-ip65/",
        ],
    },
    {
        "name": "BOARD SURFACE",
        "expected_skus": ["ILAR-03671", "ILAR-03670", "ILAR-02945"],
        "source_urls": [f"{BASE_URL}/project-details/board/"],
    },
    {
        "name": "LUNA",
        "expected_skus": ["ILAR-03679", "ILAR-03680"],
        "source_urls": [],
    },
    {
        "name": "PASCAL GU10",
        "expected_skus": ["ILAR-03740", "ILAR-03741", "ILAR-03742", "ILAR-03743", "ILAR-03744", "ILAR-03745"],
        "source_urls": [f"{BASE_URL}/project-details/luminaria-pendente-pascal/"],
    },
    {
        "name": "LUNO",
        "expected_skus": ["ILAR-03754", "ILAR-03753"],
        "source_urls": [],
    },
    {
        "name": "VIRA",
        "expected_skus": ["ILAR-03755", "ILAR-03756"],
        "source_urls": [],
    },
    {
        "name": "JULLE",
        "expected_skus": ["ILAR-03758", "ILAR-03757"],
        "source_urls": [],
    },
    {
        "name": "NOVVA",
        "expected_skus": ["ILAR-03759"],
        "source_urls": [],
    },
    {
        "name": "VIGG GU10",
        "expected_skus": ["ILAR-02452", "ILAR-02453"],
        "source_urls": [f"{BASE_URL}/project-details/vigg/", f"{BASE_URL}/project-details/vigg-white/"],
    },
    {
        "name": "LEV GU10",
        "expected_skus": ["ILAR-02454", "ILAR-02455"],
        "source_urls": [f"{BASE_URL}/project-details/downlight-saliente-lev/", f"{BASE_URL}/project-details/downlight-lev-white/"],
    },
    {
        "name": "MINI LEV GU10",
        "expected_skus": ["ILAR-03674", "ILAR-03675"],
        "source_urls": [f"{BASE_URL}/project-details/downlight-saliente-lev/", f"{BASE_URL}/project-details/downlight-lev-white/"],
    },
    {
        "name": "PRADO GU10",
        "expected_skus": ["ILAR-03068", "ILAR-03069"],
        "source_urls": [f"{BASE_URL}/project-details/prado-smart/"],
    },
]


def normalize_sku(value):
    return str(value or "").strip().upper()


def product_skus(product):
    skus = set()
    if getattr(product, "sku", None):
        skus.add(normalize_sku(product.sku))
    for variant in getattr(product, "variants", []) or []:
        sku = variant.get("sku")
        if sku:
            skus.add(normalize_sku(sku))
    return {sku for sku in skus if sku}


def target_urls(targets):
    urls = set(SKU_START_URLS)
    for target in targets:
        for url in target.get("source_urls", []):
            urls.add(url)
    return sorted(urls)


def scrape_urls(urls, crawler=None, extractor=None):
    crawler = crawler or AronlightCrawler()
    extractor = extractor or AronlightExtractor()
    pipeline = SupplierPipeline("aronlight-curated", crawler, extractor)
    direct_urls = [url for url in urls if "/project-details/" in url]
    category_urls = [url for url in urls if "/project-details/" not in url]

    products = pipeline.scrape(category_urls) if category_urls else []

    seen_urls = {getattr(product, "source_url", None) for product in products}
    for url in direct_urls:
        if url in seen_urls:
            continue
        logger.info("[aronlight-curated] Scraping direct product %s", url)
        html = crawler.fetch(url)
        product = extractor.extract(html, url)
        if product is not None:
            products.append(product)

    return products


def match_targets(products, targets):
    matched = []
    missing = []

    for target in targets:
        expected = {normalize_sku(sku) for sku in target["expected_skus"]}
        matched_products = []
        found_skus = set()

        for product in products:
            product_found = product_skus(product) & expected
            if not product_found:
                continue
            matched_products.append(product)
            found_skus.update(product_found)

        missing_skus = sorted(expected - found_skus)
        payload = {
            "name": target["name"],
            "expected_skus": sorted(expected),
            "found_skus": sorted(found_skus),
            "missing_skus": missing_skus,
            "matched_products": [
                {
                    "name": product.name,
                    "slug": product.slug,
                    "source_url": product.source_url,
                    "skus": sorted(product_skus(product)),
                }
                for product in matched_products
            ],
        }
        if matched_products:
            matched.append(payload)
        else:
            missing.append(payload)

    return {"matched": matched, "missing": missing}


def products_to_publish(products, targets):
    expected = {}
    for target in targets:
        for sku in target["expected_skus"]:
            expected[normalize_sku(sku)] = target["name"]

    selected = []
    seen = set()
    for product in products:
        skus = product_skus(product)
        if not (skus & set(expected)):
            continue
        key = getattr(product, "slug", None) or getattr(product, "source_url", None)
        if key in seen:
            continue
        seen.add(key)
        selected.append(product)
    return selected


def save_json(path, payload):
    Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def publish(products, dry_run=False):
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
        logger.info("[aronlight-curated] Publishing %s", product.slug)
        result = publisher.publish(product)
        if result:
            results.append(result)
    return results


def main(argv=None):
    cli = argparse.ArgumentParser(
        description="Scrape and publish a curated set of missing Aronlight products based on expected SKU groups.",
    )
    cli.add_argument(
        "--output-file",
        default="aronlight_curated_missing_products.json",
        help="JSON file with the scraped products considered for this curated import.",
    )
    cli.add_argument(
        "--report-file",
        default="aronlight_curated_missing_report.json",
        help="JSON file with the target matching report.",
    )
    cli.add_argument(
        "--publish",
        action="store_true",
        help="Publish matched products to Beevo.",
    )
    cli.add_argument(
        "--dry-run",
        action="store_true",
        help="When combined with --publish, do not send to Beevo.",
    )
    args = cli.parse_args(argv)

    logging.basicConfig(level=logging.INFO)

    urls = target_urls(CURATED_TARGETS)
    products = scrape_urls(urls)
    report = match_targets(products, CURATED_TARGETS)

    serializable_products = [product.__dict__ if hasattr(product, "__dict__") else product for product in products]
    save_json(args.output_file, serializable_products)
    save_json(args.report_file, report)

    selected_products = products_to_publish(products, CURATED_TARGETS)

    print(f"Scraped products: {len(products)}")
    print(f"Curated targets matched: {len(report['matched'])}")
    print(f"Curated targets still missing: {len(report['missing'])}")
    print(f"Products selected for publish: {len(selected_products)}")

    if args.publish:
        results = publish(selected_products, dry_run=args.dry_run)
        print(f"Publish results: {len(results)}")

    return {
        "scraped_products": len(products),
        "matched_targets": len(report["matched"]),
        "missing_targets": len(report["missing"]),
        "publish_candidates": len(selected_products),
    }


if __name__ == "__main__":
    main()
