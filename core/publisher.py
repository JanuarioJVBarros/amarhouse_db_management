import logging
import time
from types import SimpleNamespace

from beevo.assets import AssetsAPI
from beevo.client import BeevoClient
from beevo.labels import LabelsAPI
from beevo.options import OptionsAPI
from beevo.product import ProductAPI
from beevo.variants import VariantsAPI
from utils import json_utils

logger = logging.getLogger(__name__)


class ProductPublisher:
    """
    Orchestrates the product ingestion flow from scraped product data to Beevo.
    """

    def __init__(self, client):
        self.client = client
        self.product_api = ProductAPI(client)
        self.options_api = OptionsAPI(client)
        self.variants_api = VariantsAPI(client)
        self.assets_api = AssetsAPI(client)
        self.labels_api = LabelsAPI(client)

    def publish(self, product):
        logger.info("[PUBLISH] Starting: %s", product.slug)

        product_id = self._get_or_create_product(product)
        if not product_id:
            logger.info(
                "RESULT: [SKIP] Product already exists with correct SKU and price: %s",
                product.slug,
            )
            return None

        _, options_id = self._create_option_groups(product, product_id)
        self._create_variants(product, product_id, options_id)

        logger.info("[PUBLISH] Completed: %s", product.slug)
        return {"product_id": product_id, "status": "published"}

    def _get_or_create_product(self, product):
        logger.info("[STEP] Product create/check: %s", product.slug)
        existing = self.product_api.get_by_slug(product.slug)

        if existing:
            logger.info("RESULT: [SKIP] Product already exists: %s", product.slug)
            return existing["id"]

        product_data = {
            "name": product.name,
            "slug": product.slug,
            "description": product.description,
            "description_full": getattr(product, "description_full", None),
        }
        created = self.product_api.create_product(product_data)

        logger.info("RESULT: [DONE] Create product: %s", product.slug)
        return created["id"]

    def _create_option_groups(self, product, product_id):
        logger.info("[STEP] Creating option groups")

        final_options_id = []
        final_groups_id = []

        for group in getattr(product, "option_groups", []):
            options = group.get("options") or []

            if "-" in options:
                logger.info("RESULT: [SKIP] No options for group %s", group.get("name"))
                return None, None

            result = self.options_api.create_option_group(
                name=group.get("name"),
                options=options,
            )

            group_id = result["id"]
            options_id = result["options"]
            final_options_id.extend(options_id)
            final_groups_id.append(group_id)
            self.options_api.add_option_group_to_product(product_id, group_id)

        return final_groups_id, final_options_id

    def _create_variants(self, product, product_id, option_ids):
        logger.info("[STEP] Creating variants")

        for variant in getattr(product, "variants", []):
            variant_option_ids = []

            if option_ids and variant.get("options"):
                for option in option_ids:
                    for option_name, value in variant.get("options").items():
                        if value == option.get("name"):
                            variant_option_ids.append(option.get("id"))
                            logger.info(
                                "Matched variant option: %s -> %s",
                                option_name,
                                option.get("id"),
                            )

            if option_ids and variant.get("options") and not variant_option_ids:
                logger.info(
                    "RESULT: [SKIP] No matching option found for variant %s",
                    variant.get("name"),
                )
                continue

            self.variants_api.create_variant(
                product_id=product_id,
                name=variant.get("name"),
                sku=variant.get("sku"),
                price=variant.get("price", 0),
                stock=1000,
                option_ids=variant_option_ids,
            )

    def _upload_and_attach_assets(self, product, product_id):
        logger.info("[STEP] Uploading assets")

        asset_ids = []
        for img_url in getattr(product, "images", []):
            asset_ids.append(self.assets_api.upload_asset(img_url))

        if not asset_ids:
            logger.info("RESULT: [SKIP] No assets found")
            return

        self.assets_api.update_product_assets(product_id, asset_ids=asset_ids)
        self.assets_api.set_asset_as_featured(product_id, asset_ids[0])
        logger.info("RESULT: [DONE] Assets uploaded")

    def _attach_labels(self, product, product_id):
        logger.info("[STEP] Attaching labels")
        self.labels_api.add_labels_to_product(product_id, ["127"])


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    client = BeevoClient()
    publisher = ProductPublisher(client)

    scraped_products = json_utils.load_json("efapel_20260416_150951.json")

    print("\n=== PUBLISH RESULT ===")

    for product in scraped_products:
        product = SimpleNamespace(**product)
        publisher.publish(product)
        time.sleep(1)
