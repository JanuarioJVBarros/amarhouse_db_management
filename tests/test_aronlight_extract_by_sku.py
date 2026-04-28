from types import SimpleNamespace

from scrapers.aronlight.extract_products_by_sku import filter_products_by_skus


def build_product(sku=None, variants=None):
    return SimpleNamespace(sku=sku, variants=variants or [])


def test_filter_products_by_skus_matches_top_level_and_variant_skus():
    products = [
        build_product(sku="ILAR-00925"),
        build_product(variants=[{"sku": "ILDV-00044"}]),
        build_product(sku="ILAR-99999"),
    ]

    result = filter_products_by_skus(products, ["ILAR-00925", "ILDV-00044", "ILAR-01013"])

    assert len(result["matched_products"]) == 2
    assert result["found_skus"] == ["ILAR-00925", "ILDV-00044"]
    assert result["missing_skus"] == ["ILAR-01013"]
