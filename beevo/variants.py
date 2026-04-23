class VariantsAPI:
    def __init__(self, client):
        self.client = client

    def create_variant(self, product_id, name, sku, price, stock, option_ids, language="pt_PT"):
        """
        Creates a product variant linked to a product + options.
        Ensure option_ids are correctly mapped to the options created in the option groups step.
        """

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

        return self.client.request(
            query=query,
            variables=variables,
            operation_name="CreateProductVariants"
        )
    
    def get_product_variants_by_sku(self, sku):
        """
        Fetch product variants filtered by SKU.
        """

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
            operation_name="GetProductVariants"
        )

        return response["data"]["productVariants"]["items"]