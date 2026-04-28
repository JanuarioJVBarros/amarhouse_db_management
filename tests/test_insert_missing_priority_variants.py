from types import SimpleNamespace

from scripts.insert_missing_priority_variants import build_target_products
from scripts.insert_missing_priority_variants import ensure_product_and_variants


class StubProductAPI:
    def __init__(self, existing=None):
        self.existing = existing

    def get_by_slug(self, slug):
        return self.existing


class StubVariantsAPI:
    def __init__(self, existing_by_sku=None):
        self.existing_by_sku = existing_by_sku or {}
        self.created = []

    def get_variant_by_sku(self, sku):
        return self.existing_by_sku.get(sku)

    def create_variant(self, **kwargs):
        self.created.append(kwargs)
        return kwargs


class StubLabelsAPI:
    def __init__(self):
        self.calls = []

    def add_labels_to_product(self, product_id, facet_value_ids):
        self.calls.append((product_id, facet_value_ids))
        return {"id": product_id}


class StubPublisher:
    def __init__(self, existing=None, existing_by_sku=None):
        self.product_api = StubProductAPI(existing=existing)
        self.variants_api = StubVariantsAPI(existing_by_sku=existing_by_sku)
        self.labels_api = StubLabelsAPI()
        self.publish_calls = []

    def publish(self, product):
        self.publish_calls.append(product.slug)
        return {"product_id": product.slug, "status": "published"}

    def _attach_labels(self, product, product_id):
        facet_value_ids = getattr(product, "facet_value_ids", None) or []
        if facet_value_ids:
            self.labels_api.add_labels_to_product(product_id, [str(value) for value in facet_value_ids])


def test_build_target_products_selects_expected_families():
    products = build_target_products(["ILAR-02837", "ILAR-03671"])
    slugs = {product.slug for product in products}

    assert "module-eye-zoom" in slugs
    assert "board-surface" in slugs


def test_ensure_product_and_variants_inserts_missing_variants_into_existing_product():
    publisher = StubPublisher(
        existing={
            "id": "prod-1",
            "optionGroups": [
                {
                    "name": "Referencia",
                    "options": [
                        {"id": "opt-1", "name": "ILAR-02964"},
                        {"id": "opt-2", "name": "ILAR-02837"},
                    ],
                }
            ],
        },
        existing_by_sku={"ILAR-02964": {"id": "v-1"}},
    )
    product = SimpleNamespace(
        slug="module-eye-zoom",
        facet_value_ids=["164"],
        variants=[
            {
                "name": "MODULE EYE ZOOM ILAR-02964",
                "sku": "ILAR-02964",
                "price": 0,
                "options": {"Referencia": "ILAR-02964"},
            },
            {
                "name": "MODULE EYE ZOOM ILAR-02837",
                "sku": "ILAR-02837",
                "price": 0,
                "options": {"Referencia": "ILAR-02837"},
            },
        ],
    )

    result = ensure_product_and_variants(publisher, product, dry_run=False)

    assert result["status"] == "updated"
    assert publisher.labels_api.calls == [("prod-1", ["164"])]
    assert publisher.variants_api.created == [
        {
            "product_id": "prod-1",
            "name": "MODULE EYE ZOOM ILAR-02837",
            "sku": "ILAR-02837",
            "price": 0,
            "stock": 1000,
            "option_ids": ["opt-2"],
        }
    ]


def test_ensure_product_and_variants_publishes_full_product_when_missing():
    publisher = StubPublisher(existing=None)
    product = SimpleNamespace(slug="module-eye-zoom", variants=[], facet_value_ids=["164"])

    result = ensure_product_and_variants(publisher, product, dry_run=False)

    assert result == {"product_id": "module-eye-zoom", "status": "published"}
    assert publisher.publish_calls == ["module-eye-zoom"]
