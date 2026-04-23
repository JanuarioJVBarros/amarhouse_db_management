import time

from beevo.client import BeevoClient
from beevo.product import ProductAPI
from beevo.options import OptionsAPI
from beevo.variants import VariantsAPI
from beevo.assets import AssetsAPI
from beevo.labels import LabelsAPI
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

    # ---------------------------------------------------
    # MAIN ENTRY POINT
    # ---------------------------------------------------

    def publish(self, product):
        """
        Full ingestion pipeline
        """

        print(f"[PUBLISH] Starting: {product.slug}")

        # ===================================================
        # 1. PRODUCT
        # ===================================================
        product_id = self._get_or_create_product(product)
        if not product_id:
            print(f"RESULT: [SKIP] Product already exists with correct SKU and price: {product.slug}")
            return
        
        # ===================================================
        # 2. OPTION GROUPS
        # ===================================================
        group_id, options_id = self._create_option_groups(product, product_id)

        # ===================================================
        # 3. VARIANTS
        # ===================================================
        self._create_variants(product, product_id, options_id)

        # # ===================================================
        # # 4. IMAGES (BATCHED)
        # # ===================================================
        # self._upload_and_attach_assets(product, product_id)


        # # ===================================================
        # # 5. LABELS (FACETS)
        # # ===================================================
        # self._attach_labels(product, product_id)

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
            print(f"RESULT: [SKIP] Product already exists: {product.slug}")
            return existing["id"]

        product_data = {"name": product.name, 
                "slug": product.slug, 
                "description": product.description, 
                }
        
        created = self.product_api.create_product(product_data)

        product_id = created["data"]["createProduct"]["id"]
        print(f"RESULT: [DONE] Create product: {product.slug}")

        return product_id

    # ---------------------------------------------------
    # 2. OPTION GROUPS
    # ---------------------------------------------------
    def _create_option_groups(self, product, product_id):
        print(f"[STEP] Creating option groups")

        final_options_id = []
        final_groups_id = []
        for group in getattr(product, "option_groups", []):
            if '-' in group.get("options"):
                print(f"RESULT: [SKIP] No options for group {group.get('name')}")
                return None, None

            result = self.options_api.create_option_group(
                name=group.get("name"),
                options=group.get("options")
            )

            group_id = result["data"]["createProductOptionGroup"]["id"]
            options_id = result["data"]["createProductOptionGroup"]["options"]
            final_options_id.extend(options_id)
            final_groups_id.append(group_id)
            self.options_api.add_option_group_to_product(
                product_id,
                group_id
            )
        
        return final_groups_id, final_options_id

    # ---------------------------------------------------
    # 3. VARIANTS
    # ---------------------------------------------------

    def _create_variants(self, product, product_id, option_ids):
        print(option_ids)
        print(f"[STEP] Creating variants")
        variant_option_id = None
        variant_option_ids = []
        for variant in getattr(product, "variants", []):
            print(variant)
            if option_ids and variant.get("options"):
                for option in option_ids:
                    for option_name, value in variant.get("options").items():
                        if value == option.get("name"):
                            variant_option_id = option.get("id")
                            print(f"Matched variant option: {option_name} → {variant_option_id}")
                            variant_option_ids.append(variant_option_id)

            if variant_option_id is None and variant.get("option"):
                print(f"RESULT: [SKIP] No matching option found for variant {variant.get('name')}")
                continue

            self.variants_api.create_variant(   
                product_id=product_id,
                name=variant.get("name"),
                sku=variant.get("sku"),
                price=variant.get("price", 0),
                stock=1000,
                option_ids=variant_option_ids
            )

    # ---------------------------------------------------
    # 4. ASSETS
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

        #facet_values = getattr(product, "facet_value_ids", [])

        #if facet_values:
        self.labels_api.add_labels_to_product(
            product_id,
            ["127"]
        )
    
    # ---------------------------------------------------
    # 6. CONTENT
    # ---------------------------------------------------

    # def _update_content(self, product, product_id):
    #     print(f"[STEP] Updating content")

    #     self.content_api.update_product_content(
    #         product_id=product_id,
    #         translation_id=product_id,
    #         name=product.name,
    #         slug=product.slug,
    #         description=product.description,
    #         description_2=getattr(product, "description_2", ""),
    #         other_information=getattr(product, "other_information", ""),
    #         featured=getattr(product, "featured", False),
    #         main_collection_id=getattr(product, "main_collection_id", None),
    #         related_products_ids=getattr(product, "related_products_ids", None),
    #         google_id_id=getattr(product, "google_id_id", None)
    #     )


if __name__ == "__main__":
    client = BeevoClient()
    publisher = ProductPublisher(client)

    scraped_products = json_utils.load_json("efapel_20260416_150951.json")

    print("\n=== PUBLISH RESULT ===")

    for product in scraped_products:
        product = SimpleNamespace(**product)
        result = publisher.publish(product)
        time.sleep(1)
