from types import SimpleNamespace

import requests

from scrapers.aronlight.targeted_pipeline import compare_products
from scrapers.aronlight.targeted_pipeline import scrape_target_urls


def build_product(name, slug, source_url, sku=None, variants=None):
    return SimpleNamespace(
        name=name,
        slug=slug,
        source_url=source_url,
        sku=sku,
        variants=variants or [],
    )


def test_compare_products_matches_by_source_url():
    scraped = [
        build_product(
            name="ACE",
            slug="ace",
            source_url="https://aronlight.com/project-details/luminaria-encastrar-ace/",
            sku="ILAR-00662",
        )
    ]
    baseline = [
        {
            "source_url": "https://aronlight.com/project-details/luminaria-encastrar-ace/",
            "sku": "ILAR-00662",
            "variants": [],
        }
    ]

    result = compare_products(scraped, baseline)

    assert len(result["matched"]) == 1
    assert len(result["missing"]) == 0


def test_compare_products_matches_by_variant_sku_when_url_differs():
    scraped = [
        build_product(
            name="Linear Modular Light",
            slug="linear-modular-light",
            source_url="https://aronlight.com/project-details/linear-modular-light/",
            variants=[{"sku": "ILAR-02112"}],
        )
    ]
    baseline = [
        {
            "source_url": "https://aronlight.com/project-details/another-url/",
            "sku": None,
            "variants": [{"sku": "ILAR-02112"}],
        }
    ]

    result = compare_products(scraped, baseline)

    assert len(result["matched"]) == 1
    assert len(result["missing"]) == 0


def test_compare_products_reports_missing_products():
    scraped = [
        build_product(
            name="TIDE",
            slug="tide",
            source_url="https://aronlight.com/project-details/luminaria-tide/",
            sku="ILAR-99999",
        )
    ]
    baseline = []

    result = compare_products(scraped, baseline)

    assert len(result["matched"]) == 0
    assert len(result["missing"]) == 1


class FailingCrawler:
    def fetch(self, url):
        raise requests.HTTPError("404 Client Error")


def test_scrape_target_urls_skips_fetch_failures():
    products = scrape_target_urls(
        ["https://aronlight.com/project-details/vigg/"],
        crawler=FailingCrawler(),
        extractor=None,
    )

    assert products == []
