from types import SimpleNamespace

import requests

from core.publisher import ProductPublisher


class DummyClient:
    pass


class StubProductAPI:
    def __init__(self):
        self.created_products = []
        self.existing = None

    def get_by_slug(self, slug):
        return self.existing

    def create_product(self, product_data):
        self.created_products.append(product_data)
        return {"id": "prod-1", "name": product_data["name"], "slug": product_data["slug"]}


class StubOptionsAPI:
    def __init__(self):
        self.created_groups = []
        self.attached_groups = []

    def create_option_group(self, name, options):
        created = {
            "id": f"group-{len(self.created_groups) + 1}",
            "name": name,
            "options": [
                {"id": f"opt-{len(self.created_groups) + 1}-{index}", "name": option}
                for index, option in enumerate(options, start=1)
            ],
        }
        self.created_groups.append(created)
        return created

    def add_option_group_to_product(self, product_id, group_id):
        self.attached_groups.append((product_id, group_id))
        return {"id": product_id, "optionGroups": [{"id": group_id}]}


class StubVariantsAPI:
    def __init__(self):
        self.created_variants = []
        self.existing_by_sku = {}

    def create_variant(self, **kwargs):
        self.created_variants.append(kwargs)
        return {"id": f"variant-{len(self.created_variants)}", **kwargs}

    def get_variant_by_sku(self, sku):
        return self.existing_by_sku.get(sku)


class StubAssetsAPI:
    def __init__(self):
        self.uploaded_images = []
        self.updated_products = []
        self.featured_assets = []

    def upload_asset(self, image_url):
        self.uploaded_images.append(image_url)
        return "asset-1"

    def update_product_assets(self, product_id, asset_ids):
        self.updated_products.append((product_id, asset_ids))
        return {"id": product_id, "assets": asset_ids}

    def set_asset_as_featured(self, product_id, asset_id):
        self.featured_assets.append((product_id, asset_id))
        return {"id": product_id, "featuredAsset": {"id": asset_id}}


class FlakyAssetsAPI(StubAssetsAPI):
    def upload_asset(self, image_url):
        if "broken" in image_url:
            raise requests.HTTPError("404 Client Error")
        return super().upload_asset(image_url)


class StubLabelsAPI:
    def __init__(self):
        self.calls = []

    def add_labels_to_product(self, product_id, facet_value_ids):
        self.calls.append((product_id, facet_value_ids))
        return {"id": product_id}


def build_publisher():
    publisher = ProductPublisher(DummyClient())
    publisher.product_api = StubProductAPI()
    publisher.options_api = StubOptionsAPI()
    publisher.variants_api = StubVariantsAPI()
    publisher.assets_api = StubAssetsAPI()
    publisher.labels_api = StubLabelsAPI()
    return publisher


def test_publish_creates_product_using_normalized_return_shape():
    publisher = build_publisher()
    product = SimpleNamespace(
        name="Wall Lamp",
        slug="wall-lamp",
        description="A lamp",
        description_full="Long description",
        images=["https://example.test/image.jpg"],
        facet_value_ids=["164"],
        option_groups=[],
        variants=[],
    )

    result = publisher.publish(product)

    assert result == {"product_id": "prod-1", "status": "published"}
    assert publisher.product_api.created_products[0]["description_full"] == "Long description"
    assert publisher.assets_api.uploaded_images == ["https://example.test/image.jpg"]
    assert publisher.assets_api.updated_products == [("prod-1", ["asset-1"])]
    assert publisher.assets_api.featured_assets == [("prod-1", "asset-1")]
    assert publisher.labels_api.calls == [("prod-1", ["164"])]


def test_create_variants_does_not_leak_option_ids_between_variants():
    publisher = build_publisher()
    product = SimpleNamespace(
        variants=[
            {
                "name": "Variant A",
                "sku": "A",
                "price": 100,
                "options": {"Color": "White"},
            },
            {
                "name": "Variant B",
                "sku": "B",
                "price": 200,
                "options": {"Color": "Black"},
            },
        ]
    )
    option_ids = [
        {"id": "opt-white", "name": "White"},
        {"id": "opt-black", "name": "Black"},
    ]

    publisher._create_variants(product, "prod-1", option_ids)

    assert publisher.variants_api.created_variants[0]["option_ids"] == ["opt-white"]
    assert publisher.variants_api.created_variants[1]["option_ids"] == ["opt-black"]


def test_create_variants_matches_options_by_group_name():
    publisher = build_publisher()
    product = SimpleNamespace(
        option_groups=[
            {"name": "Frame Color", "options": ["White", "Black"]},
            {"name": "Light Color", "options": ["White", "Warm"]},
        ],
        variants=[
            {
                "name": "Variant A",
                "sku": "A",
                "price": 100,
                "options": {
                    "Frame Color": "White",
                    "Light Color": "Warm",
                },
            }
        ],
    )
    option_groups = [
        {
            "name": "Frame Color",
            "options": [
                {"id": "frame-white", "name": "White"},
                {"id": "frame-black", "name": "Black"},
            ],
        },
        {
            "name": "Light Color",
            "options": [
                {"id": "light-white", "name": "White"},
                {"id": "light-warm", "name": "Warm"},
            ],
        },
    ]

    publisher._create_variants(product, "prod-1", option_groups)

    assert publisher.variants_api.created_variants == [
        {
            "product_id": "prod-1",
            "name": "Variant A",
            "sku": "A",
            "price": 100,
            "stock": 1000,
            "option_ids": ["frame-white", "light-warm"],
        }
    ]


def test_create_option_groups_uses_normalized_group_shape():
    publisher = build_publisher()
    product = SimpleNamespace(
        option_groups=[
            {"name": "Color", "options": ["White", "Black"]},
        ]
    )

    groups = publisher._create_option_groups(product, "prod-1")

    assert groups == [
        {
            "id": "group-1",
            "name": "Color",
            "options": [
                {"id": "opt-1-1", "name": "White"},
                {"id": "opt-1-2", "name": "Black"},
            ],
        }
    ]


def test_create_option_groups_skips_placeholder_only_groups():
    publisher = build_publisher()
    product = SimpleNamespace(
        option_groups=[
            {"name": "Invalid", "options": ["-"]},
            {"name": "Color", "options": ["White", "Black"]},
        ]
    )

    groups = publisher._create_option_groups(product, "prod-1")

    assert groups == [
        {
            "id": "group-1",
            "name": "Color",
            "options": [
                {"id": "opt-1-1", "name": "White"},
                {"id": "opt-1-2", "name": "Black"},
            ],
        }
    ]


def test_publish_skips_asset_upload_when_product_has_no_images():
    publisher = build_publisher()
    product = SimpleNamespace(
        name="No Image Lamp",
        slug="no-image-lamp",
        description="A lamp",
        description_full=None,
        images=[],
        facet_value_ids=[],
        option_groups=[],
        variants=[],
    )

    publisher.publish(product)

    assert publisher.assets_api.uploaded_images == []
    assert publisher.assets_api.updated_products == []
    assert publisher.assets_api.featured_assets == []


def test_publish_skips_broken_assets_and_continues():
    publisher = build_publisher()
    publisher.assets_api = FlakyAssetsAPI()
    product = SimpleNamespace(
        name="Lamp",
        slug="lamp",
        description="A lamp",
        description_full=None,
        images=[
            "https://example.test/broken.png",
            "https://example.test/good.jpg",
        ],
        facet_value_ids=[],
        option_groups=[],
        variants=[],
    )

    result = publisher.publish(product)

    assert result == {"product_id": "prod-1", "status": "published"}
    assert publisher.assets_api.uploaded_images == ["https://example.test/good.jpg"]
    assert publisher.assets_api.updated_products == [("prod-1", ["asset-1"])]
    assert publisher.assets_api.featured_assets == [("prod-1", "asset-1")]


def test_publish_skips_existing_product_without_recreating_variants_or_assets():
    publisher = build_publisher()
    publisher.product_api.existing = {"id": "prod-existing", "slug": "wall-lamp"}
    product = SimpleNamespace(
        name="Wall Lamp",
        slug="wall-lamp",
        description="A lamp",
        description_full="Long description",
        images=["https://example.test/image.jpg"],
        facet_value_ids=["164"],
        option_groups=[{"name": "Temp (K)", "options": ["3000", "4000"]}],
        variants=[
            {
                "name": "Wall Lamp",
                "sku": "SKU-1",
                "price": 100,
                "options": {"Temp (K)": "3000"},
            }
        ],
    )

    result = publisher.publish(product)

    assert result is None
    assert publisher.options_api.created_groups == []
    assert publisher.variants_api.created_variants == []
    assert publisher.assets_api.uploaded_images == []


def test_publish_skips_when_any_sku_already_exists():
    publisher = build_publisher()
    publisher.variants_api.existing_by_sku = {
        "EC-3337": {"id": "variant-existing", "sku": "EC-3337"}
    }
    product = SimpleNamespace(
        name="ALBA E14 7W",
        slug="alba-e14-7w-new",
        sku="EC-3337",
        description="Bombilla ALBA",
        description_full=None,
        images=["https://example.test/image.jpg"],
        facet_value_ids=["164"],
        option_groups=[{"name": "Temp (K)", "options": ["3.000", "4.200", "6.000"]}],
        variants=[
            {
                "name": "ALBA E14 7W",
                "sku": "EC-3337",
                "price": 0,
                "options": {"Temp (K)": "3.000"},
            }
        ],
    )

    result = publisher.publish(product)

    assert result is None
    assert publisher.product_api.created_products == []
    assert publisher.options_api.created_groups == []
    assert publisher.variants_api.created_variants == []
    assert publisher.assets_api.uploaded_images == []


def test_create_variants_skips_partial_option_sets():
    publisher = build_publisher()
    product = SimpleNamespace(
        option_groups=[
            {"name": "Color", "options": ["White", "Black"]},
            {"name": "Temp (K)", "options": ["3000", "4000"]},
        ],
        variants=[
            {
                "name": "Incomplete Variant",
                "sku": "SKU-1",
                "price": 100,
                "options": {"Color": "White"},
            }
        ],
    )
    option_ids = [
        {"id": "opt-white", "name": "White"},
        {"id": "opt-black", "name": "Black"},
        {"id": "opt-3000", "name": "3000"},
        {"id": "opt-4000", "name": "4000"},
    ]

    publisher._create_variants(product, "prod-1", option_ids)

    assert publisher.variants_api.created_variants == []


def test_create_variants_skips_duplicate_option_combinations():
    publisher = build_publisher()
    product = SimpleNamespace(
        option_groups=[
            {"name": "Temp (K)", "options": ["3000", "4000"]},
        ],
        variants=[
            {
                "name": "Variant A",
                "sku": "SKU-1",
                "price": 100,
                "options": {"Temp (K)": "3000"},
            },
            {
                "name": "Variant B",
                "sku": "SKU-2",
                "price": 100,
                "options": {"Temp (K)": "3000"},
            },
        ],
    )
    option_ids = [
        {"id": "opt-3000", "name": "3000"},
        {"id": "opt-4000", "name": "4000"},
    ]

    publisher._create_variants(product, "prod-1", option_ids)

    assert publisher.variants_api.created_variants == [
        {
            "product_id": "prod-1",
            "name": "Variant A",
            "sku": "SKU-1",
            "price": 100,
            "stock": 1000,
            "option_ids": ["opt-3000"],
        }
    ]


def test_publish_skips_label_attachment_when_product_has_no_labels():
    publisher = build_publisher()
    product = SimpleNamespace(
        name="Wall Lamp",
        slug="wall-lamp-no-labels",
        description="A lamp",
        description_full=None,
        images=[],
        facet_value_ids=[],
        option_groups=[],
        variants=[],
    )

    publisher.publish(product)

    assert publisher.labels_api.calls == []


def test_create_variants_allows_multiple_variants_without_option_groups():
    publisher = build_publisher()
    product = SimpleNamespace(
        option_groups=[],
        variants=[
            {
                "name": "Variant A",
                "sku": "SKU-1",
                "price": 100,
                "options": {},
            },
            {
                "name": "Variant B",
                "sku": "SKU-2",
                "price": 100,
                "options": {},
            },
        ],
    )

    publisher._create_variants(product, "prod-1", option_ids=[])

    assert publisher.variants_api.created_variants == [
        {
            "product_id": "prod-1",
            "name": "Variant A",
            "sku": "SKU-1",
            "price": 100,
            "stock": 1000,
            "option_ids": [],
        },
        {
            "product_id": "prod-1",
            "name": "Variant B",
            "sku": "SKU-2",
            "price": 100,
            "stock": 1000,
            "option_ids": [],
        },
    ]
