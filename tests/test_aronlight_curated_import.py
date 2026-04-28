from types import SimpleNamespace

from scrapers.aronlight.import_curated_missing_products import match_targets
from scrapers.aronlight.import_curated_missing_products import products_to_publish


def build_product(name, slug, source_url, sku=None, variants=None):
    return SimpleNamespace(
        name=name,
        slug=slug,
        source_url=source_url,
        sku=sku,
        variants=variants or [],
    )


def test_match_targets_collects_found_and_missing_skus():
    products = [
        build_product(
            name="Board Surface",
            slug="board-surface",
            source_url="https://aronlight.com/project-details/board/",
            sku="ILAR-02945",
            variants=[],
        )
    ]
    targets = [
        {
            "name": "BOARD SURFACE",
            "expected_skus": ["ILAR-03671", "ILAR-03670", "ILAR-02945"],
            "source_urls": [],
        }
    ]

    result = match_targets(products, targets)

    assert result["matched"][0]["found_skus"] == ["ILAR-02945"]
    assert result["matched"][0]["missing_skus"] == ["ILAR-03670", "ILAR-03671"]


def test_products_to_publish_selects_unique_matching_products():
    products = [
        build_product(
            name="Board Surface",
            slug="board-surface",
            source_url="https://aronlight.com/project-details/board/",
            sku="ILAR-02945",
        ),
        build_product(
            name="Board Surface duplicate",
            slug="board-surface",
            source_url="https://aronlight.com/project-details/board/",
            sku="ILAR-02945",
        ),
    ]
    targets = [
        {
            "name": "BOARD SURFACE",
            "expected_skus": ["ILAR-02945"],
            "source_urls": [],
        }
    ]

    selected = products_to_publish(products, targets)

    assert len(selected) == 1
    assert selected[0].slug == "board-surface"
