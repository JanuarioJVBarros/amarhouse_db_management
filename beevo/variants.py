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

        variants = response.get("data", {}).get("createProductVariants")

        assert variants, f"Variant creation failed: {response}"

        variant = variants[0] if isinstance(variants, list) else variants

        assert variant.get("sku") == sku, "SKU mismatch after creation"
        assert variant.get("price") == price, "Price mismatch after creation"

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

        items = response.get("data", {}).get("productVariants", {}).get("items", [])

        assert isinstance(items, list), "Invalid response structure for variants list"

        return items
