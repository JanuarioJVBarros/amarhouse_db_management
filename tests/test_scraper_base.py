from scrapers.base.normalizers import (
    build_scraped_product,
    clean_text,
    normalize_images,
    normalize_labels,
    slugify,
    unique_strings,
)
from scrapers.base.pipeline import SupplierPipeline


class DummyCrawler:
    def __init__(self):
        self.crawled = []
        self.fetched = []

    def crawl_category(self, start_url):
        self.crawled.append(start_url)
        return [f"{start_url}/product-1", f"{start_url}/product-2"]

    def fetch(self, url):
        self.fetched.append(url)
        return f"<html>{url}</html>"


class DummyExtractor:
    def extract(self, html, url):
        return build_scraped_product(
            name=f"Product for {url}",
            images=["https://example.test/image.jpg", "https://example.test/image.jpg"],
            labels=["supplier", "supplier"],
            source_url=url,
        )


def test_clean_text_collapses_whitespace():
    assert clean_text("  Wall   Lamp \n ") == "Wall Lamp"


def test_unique_strings_filters_empty_and_duplicate_values():
    assert unique_strings([" one ", "", None, "one", "two"]) == ["one", "two"]


def test_slugify_normalizes_text():
    assert slugify("Wall Lamp / 2000K") == "wall-lamp-2000k"


def test_build_scraped_product_normalizes_common_fields():
    product = build_scraped_product(
        name="  Wall Lamp  ",
        description="  Short   description ",
        images=["https://example.test/a.jpg", "https://example.test/a.jpg"],
        labels=["indoor", "indoor", "lighting"],
        source_url=" https://example.test/p/1 ",
    )

    assert product.name == "Wall Lamp"
    assert product.slug == "wall-lamp"
    assert product.description == "Short description"
    assert product.images == ["https://example.test/a.jpg"]
    assert product.labels == ["indoor", "lighting"]
    assert product.source_url == "https://example.test/p/1"


def test_normalize_images_and_labels_keep_unique_strings():
    assert normalize_images([" a ", "a", "b "]) == ["a", "b"]
    assert normalize_labels([" x ", "x", "y "]) == ["x", "y"]


def test_supplier_pipeline_scrapes_all_urls():
    crawler = DummyCrawler()
    extractor = DummyExtractor()
    pipeline = SupplierPipeline("dummy", crawler, extractor)

    products = pipeline.scrape(["https://example.test/category"])

    assert crawler.crawled == ["https://example.test/category"]
    assert crawler.fetched == [
        "https://example.test/category/product-1",
        "https://example.test/category/product-2",
    ]
    assert len(products) == 2
    assert products[0].labels == ["supplier"]


def test_supplier_pipeline_default_output_file_contains_supplier_name():
    pipeline = SupplierPipeline("ecolux", DummyCrawler(), DummyExtractor())
    output_name = pipeline.default_output_file()

    assert output_name.startswith("ecolux_")
    assert output_name.endswith(".json")
