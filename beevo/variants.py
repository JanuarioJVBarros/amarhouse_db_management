from beevo.exceptions import BeevoValidationError
from beevo.validation import require_list, require_mapping, require_path


class VariantsAPI:
    def __init__(self, client):
        self.client = client


    def create_variant(
        self,
        product_id,
        name,
        sku,
        price,
        stock,
        option_ids,
        language="pt_PT",
        expected_status=200
    ):
        query = """
        mutation CreateProductVariants($input: [CreateProductVariantInput!]!) {
            createProductVariants(input: $input) {
                id
                sku
                price
                options {
                    code
                    name
                }
            }
        }
        """

        variables = {
            "input": [
                {
                    "productId": product_id,
                    "enabled": True,
                    "sku": sku,
                    "price": price,
                    "translations": [
                        {
                            "languageCode": language,
                            "name": name
                        }
                    ],
                    "stockLevels": [
                        {
                            "stockLocationId": "1",
                            "stockOnHand": stock
                        }
                    ],
                    "optionIds": option_ids or []
                }
            ]
        }

        response = self.client.request(
            query=query,
            variables=variables,
            operation_name="CreateProductVariants",
            expected_status=expected_status
        )

        variants = require_list(
            require_path(response, ["data", "createProductVariants"], "create_variant response"),
            "create_variant response.data.createProductVariants",
        )

        if not variants:
            raise BeevoValidationError("Variant creation returned an empty list")

        variant = require_mapping(variants[0], "create_variant first variant")

        if variant.get("sku") != sku:
            raise BeevoValidationError("SKU mismatch after creation")

        if variant.get("price") != price:
            raise BeevoValidationError("Price mismatch after creation")

        return variant


    def get_product_variants_by_sku(self, sku, expected_status=200):
        query = """
        query GetProductVariants($options: ProductVariantListOptions) {
            productVariants(options: $options) {
                items {
                    id
                    name
                    sku
                    price
                }
            }
        }
        """

        variables = {
            "options": {
                "filter": {
                    "sku": {
                        "eq": sku
                    }
                }
            }
        }

        response = self.client.request(
            query=query,
            variables=variables,
            operation_name="GetProductVariants",
            expected_status=expected_status
        )

        items = require_list(
            require_path(response, ["data", "productVariants", "items"], "get_product_variants_by_sku response"),
            "get_product_variants_by_sku response.data.productVariants.items",
        )

        return items


    def get_variant_by_sku(self, sku, expected_status=200):
        items = self.get_product_variants_by_sku(sku, expected_status=expected_status)
        return items[0] if items else None
    

    def get_all_variants(self):
        query = """
        query GetVariants($options: ProductVariantListOptions) {
            productVariants(options: $options) {
                items {
                    id
                    sku
                    price
                }
                totalItems
            }
        }
        """

        all_variants = []
        skip = 0
        take = 100  # safe batch size

        while True:
            variables = {
                "options": {
                    "skip": skip,
                    "take": take
                }
            }

            response = self.client.request(query=query, variables=variables, operation_name="GetVariants")
            data = require_mapping(
                require_path(response, ["data", "productVariants"], "get_all_variants response"),
                "get_all_variants response.data.productVariants",
            )

            items = require_list(data.get("items"), "get_all_variants items")
            total = data.get("totalItems")

            if not isinstance(total, int):
                raise BeevoValidationError("get_all_variants totalItems must be an integer")

            all_variants.extend(items)

            print(f"[FETCH] {len(all_variants)}/{total}")

            if len(all_variants) >= total:
                break

            skip += take

        return all_variants
    
    def build_variant_lookup(self):
        variants = self.get_all_variants()

        lookup = {}

        for v in variants:
            sku = v.get("sku")

            if not sku:
                continue

            sku = sku.strip().upper()

            lookup[sku] = {
                "id": v["id"],
                "price": v["price"]
            }

        print(f"[INFO] Loaded {len(lookup)} variants into lookup")

        return lookup

    def update_variant(
        self,
        variant_id,
        price=None,
        sku=None,
        enabled=None,
        name=None,
        language="pt_PT",
        expected_status=200
    ):
        query = """
        mutation UpdateProductVariant($input: UpdateProductVariantInput!) {
            updateProductVariant(input: $input) {
                id
                sku
                price
                enabled
                name
            }
        }
        """

        payload = {"id": variant_id}

        if price is not None:
            payload["price"] = price

        if sku is not None:
            payload["sku"] = sku

        if enabled is not None:
            payload["enabled"] = enabled

        if name is not None:
            payload["translations"] = [
                {
                    "languageCode": language,
                    "name": name
                }
            ]

        if len(payload) <= 1:
            raise BeevoValidationError("update_variant requires at least one field to update")

        response = self.client.request(
            query=query,
            variables={"input": payload},
            operation_name="UpdateProductVariant",
            expected_status=expected_status
        )

        updated = require_mapping(
            require_path(response, ["data", "updateProductVariant"], "update_variant response"),
            "update_variant response.data.updateProductVariant",
        )

        if price is not None:
            if updated.get("price") != price:
                raise BeevoValidationError("Price not updated correctly")

        if sku is not None:
            if updated.get("sku") != sku:
                raise BeevoValidationError("SKU not updated correctly")

        if enabled is not None:
            if updated.get("enabled") != enabled:
                raise BeevoValidationError("Enabled flag not updated correctly")

        if name is not None:
            if updated.get("name") != name:
                raise BeevoValidationError("Name not updated correctly")

        return updated

    def update_price_by_sku(self, sku, price):
        variant = self.get_variant_by_sku(sku)

        if not variant:
            print(f"[SKIP] SKU not found: {sku}")
            return

        self.update_variant(
            variant_id=variant["id"],
            price=int(price * 100)
        )

        print(f"[OK] {sku} → {price}")
