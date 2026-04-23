import time

from beevo.client import BeevoClient
from beevo.product import ProductAPI
from beevo.options import OptionsAPI
from beevo.variants import VariantsAPI
from beevo.assets import AssetsAPI
from beevo.labels import LabelsAPI
from beevo.content import ContentAPI
from utils import json_utils

from types import SimpleNamespace

class ProductPublisher:
    """
    Orchestrates full product ingestion pipeline:
    Scraped Product → Beevo CMS
    """

    def __init__(self, client):
        self.client = client

        self.product_api = ProductAPI(client)
        self.options_api = OptionsAPI(client)
        self.variants_api = VariantsAPI(client)
        self.assets_api = AssetsAPI(client)
        self.labels_api = LabelsAPI(client)
        self.content_api = ContentAPI(client)

    # ---------------------------------------------------
    # MAIN ENTRY POINT
    # ---------------------------------------------------

    def publish(self, product):
        """
        Full ingestion pipeline
        """

        print(f"[PUBLISH] Starting: {product.slug}")

        # ===================================================
        # 1. PRODUCT (IDEMPOTENT)
        # ===================================================
        product_id, variant_id = self._get_or_create_product(product)
        if not product_id:
            print(f"RESULT: [SKIP] Product already exists with correct SKU and price: {product.slug}")
            return
        # ===================================================
        # 2. OPTION GROUPS
        # ===================================================
        option_group_ids = self._create_option_groups(product, product_id)

        # ===================================================
        # 3. VARIANTS
        # ===================================================
        self._create_variants(product, product_id)

        # ===================================================
        # 4. IMAGES (BATCHED)
        # ===================================================
        self._upload_and_attach_assets(product, product_id)

        # ===================================================
        # 5. LABELS (FACETS)
        # ===================================================
        self._attach_labels(product, product_id)

        # ===================================================
        # 6. CONTENT (DESCRIPTION + CMS FIELDS)
        # ===================================================
        #self._update_content(product, product_id)

        # ===================================================
        # FINAL RESULT
        # ===================================================
        print(f"[PUBLISH] Completed: {product.slug}")

        return {
            "product_id": product_id,
            "status": "published"
        }

    # ---------------------------------------------------
    # 1. PRODUCT (IDEMPOTENT)
    # ---------------------------------------------------

    def _get_or_create_product(self, product):
        print(f"[STEP] Product create/check: {product.slug}")

        existing = self.product_api.get_by_slug(product.slug)

        if existing:
            # ensure that sku and price matches the expected
            variant_list = self.variants_api.get_product_variants_by_sku(product.sku)
            if variant_list:
                variant_id = variant_list[0]["id"]
                self.product_api.update_sku(variant_id, product.sku)
                self.product_api.update_price(variant_id, product.price)
                #return existing["id"], variant_id
                return None, None
            print(f"RESULT: [SKIP] Product already exists: {product.slug}")
            return existing["id"], None

        product_data = {"name": product.name, 
                        "slug": product.slug, 
                        "description": product.description, 
                        "description_full": product.description_full,
                        "price": product.price,
                        "sku": product.sku
                        }
        
        created = self.product_api.create_product(product_data)

        product_id = created["data"]["createProduct"]["id"]
        response = self.product_api.create_first_variant(product_id, product_data)
        print(response)
        if response:
            variant_id = response["data"]["createProductVariants"][0]["id"]
        else:
            variant_id = None
        print(f"RESULT: [DONE] Create product: {product.slug}")

        return product_id, variant_id

    # ---------------------------------------------------
    # 2. OPTION GROUPS
    # ---------------------------------------------------

    def _create_option_groups(self, product, product_id):
        print(f"[STEP] Creating option groups")

        option_group_map = {}

        for group in getattr(product, "option_groups", []):

            result = self.options_api.create_option_group(
                code=group.code,
                name=group.name,
                options=[
                    {"code": opt.code, "name": opt.name}
                    for opt in group.options
                ]
            )

            group_id = result["createProductOptionGroup"]["id"]

            self.options_api.add_option_group_to_product(
                product_id,
                group_id
            )

            option_group_map[group.code] = group_id

        return option_group_map

    # ---------------------------------------------------
    # 3. VARIANTS
    # ---------------------------------------------------

    def _create_variants(self, product, product_id):
        print(f"[STEP] Creating variants")

        for variant in getattr(product, "variants", []):

            self.variants_api.create_variant(
                product_id=product_id,
                sku=variant.sku,
                price=variant.price,
                stock=variant.stock,
                option_ids=self._resolve_option_ids(variant)
            )

    def _resolve_option_ids(self, variant):
        """
        Ensures correct mapping between codes and IDs.
        Replace if your API already returns IDs.
        """
        return getattr(variant, "option_ids", variant.option_codes)

    # ---------------------------------------------------
    # 4. ASSETS (BATCHED)
    # ---------------------------------------------------

    def _upload_and_attach_assets(self, product, product_id):
        print(f"[STEP] Uploading assets")

        asset_ids = []

        for img_url in getattr(product, "images", []):

            asset_id = self.assets_api.upload_asset(img_url)
            asset_ids.append(asset_id)

        if not asset_ids:
            print(f"RESULT: [SKIP] No assets found")
            return

        response = self.assets_api.update_product_assets(product_id, asset_ids=asset_ids)
        response = self.assets_api.set_asset_as_featured(product_id, asset_ids[0])
        
        print(f"RESULT: [DONE] Assets uploaded")

    # ---------------------------------------------------
    # 5. LABELS (FACETS)
    # ---------------------------------------------------

    def _attach_labels(self, product, product_id):
        print(f"[STEP] Attaching labels")

        facet_values = getattr(product, "facet_value_ids", [])

        #if facet_values:
        self.labels_api.add_labels_to_product(
            product_id,
            ["92", "89", "90", "91"]
        )

    # ---------------------------------------------------
    # 6. CONTENT
    # ---------------------------------------------------

    def _update_content(self, product, product_id):
        print(f"[STEP] Updating content")

        self.content_api.update_product_content(
            product_id=product_id,
            translation_id=product_id,
            name=product.name,
            slug=product.slug,
            description=product.description,
            description_2=getattr(product, "description_2", ""),
            other_information=getattr(product, "other_information", ""),
            featured=getattr(product, "featured", False),
            main_collection_id=getattr(product, "main_collection_id", None),
            related_products_ids=getattr(product, "related_products_ids", None),
            google_id_id=getattr(product, "google_id_id", None)
        )


if __name__ == "__main__":
    client = BeevoClient()
    publisher = ProductPublisher(client)

    scraped_products = json_utils.load_json("scraped_products copy.json")

    print("\n=== PUBLISH RESULT ===")

    for product in scraped_products:
        product = SimpleNamespace(**product)
        result = publisher.publish(product)
        time.sleep(1)