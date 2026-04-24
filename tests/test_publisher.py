from types import SimpleNamespace

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

    def create_variant(self, **kwargs):
        self.created_variants.append(kwargs)
        return {"id": f"variant-{len(self.created_variants)}", **kwargs}


class StubAssetsAPI:
    def upload_asset(self, image_url):
        return "asset-1"

    def update_product_assets(self, product_id, asset_ids):
        return {"id": product_id, "assets": asset_ids}

    def set_asset_as_featured(self, product_id, asset_id):
        return {"id": product_id, "featuredAsset": {"id": asset_id}}


class StubLabelsAPI:
    def add_labels_to_product(self, product_id, facet_value_ids):
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
        option_groups=[],
        variants=[],
    )

    result = publisher.publish(product)

    assert result == {"product_id": "prod-1", "status": "published"}
    assert publisher.product_api.created_products[0]["description_full"] == "Long description"


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


def test_create_option_groups_uses_normalized_group_shape():
    publisher = build_publisher()
    product = SimpleNamespace(
        option_groups=[
            {"name": "Color", "options": ["White", "Black"]},
        ]
    )

    group_ids, option_ids = publisher._create_option_groups(product, "prod-1")

    assert group_ids == ["group-1"]
    assert option_ids == [
        {"id": "opt-1-1", "name": "White"},
        {"id": "opt-1-2", "name": "Black"},
    ]
