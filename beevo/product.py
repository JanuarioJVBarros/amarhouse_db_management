class ProductAPI:
    def __init__(self, client):
        self.client = client


    def create_product(self, product_data, expected_status=200):
        query = """
        mutation CreateProduct($input: CreateProductInput!) {
            createProduct(input: $input) {
                id
                name
                slug
            }
        }
        """

        variables = {
            "input": {
                "enabled": True,
                "assetIds": [],
                "facetValueIds": [],
                "translations": [
                    {
                        "languageCode": "pt_PT",
                        "name": product_data.get("name"),
                        "slug": product_data.get("slug"),
                        "description": product_data.get("description", ""),
                        "customFields": {
                            "description_2": product_data.get("description_full"),
                            "other_information": None,
                        }
                    }
                ],
                "customFields": {
                    "featured": False,
                    "mainCollectionId": None,
                    "relatedProductsIds": [],
                    "googleIdId": None
                }
            }
        }

        response = self.client.request(
            query=query,
            variables=variables,
            operation_name="CreateProduct",
            expected_status=expected_status
        )

        product = response.get("data", {}).get("createProduct")

        assert product is not None, f"Product creation failed: {response}"
        assert product.get("id"), "Missing product ID"
        assert product.get("name") == product_data.get("name"), "Product name mismatch"

        return product


    def create_first_variant(self, product_id, product_data, expected_status=200):
        query = """<KEEP ORIGINAL QUERY>"""

        variables = {
            "input": [
                {
                    "productId": product_id,
                    "price": product_data.get("price", 0),
                    "sku": product_data.get("sku"),
                    "translations": [
                        {
                            "languageCode": "pt_PT",
                            "name": product_data.get("name")
                        }
                    ],
                    "stockLevels": [
                        {
                            "stockLocationId": "1",
                            "stockOnHand": 1000
                        }
                    ],
                    "optionIds": []
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

        return variants[0] if isinstance(variants, list) else variants


    def get_by_slug(self, slug, expected_status=200):
        query = """
        query GetProducts($options: ProductListOptions) {
            products(options: $options) {
                items {
                    id
                    name
                    slug
                }
            }
        }
        """

        variables = {
            "options": {
                "filter": {
                    "slug": {
                        "eq": slug
                    }
                }
            }
        }

        response = self.client.request(
            query=query,
            variables=variables,
            operation_name="GetProducts",
            expected_status=expected_status
        )

        items = response.get("data", {}).get("products", {}).get("items", [])

        return items[0] if items else None


    def update_sku(self, variant_id, sku, expected_status=200):
        query = """
        mutation UpdateProductVariant($input: UpdateProductVariantInput!) {
            updateProductVariant(input: $input) {
                id
                sku
            }
        }
        """

        variables = {
            "input": {
                "id": variant_id,
                "sku": sku
            }
        }

        response = self.client.request(
            query=query,
            variables=variables,
            operation_name="UpdateProductVariant",
            expected_status=expected_status
        )

        updated = response.get("data", {}).get("updateProductVariant")

        assert updated is not None, f"SKU update failed: {response}"
        assert updated.get("sku") == sku, "SKU not updated correctly"

        return updated

    # -------------------------
    # UPDATE PRICE
    # -------------------------
    def update_price(self, variant_id, price, expected_status=200):
        query = """
        mutation UpdateProductVariant($input: UpdateProductVariantInput!) {
            updateProductVariant(input: $input) {
                id
                price
            }
        }
        """

        variables = {
            "input": {
                "id": variant_id,
                "price": price
            }
        }

        response = self.client.request(
            query=query,
            variables=variables,
            operation_name="UpdateProductVariant",
            expected_status=expected_status
        )

        updated = response.get("data", {}).get("updateProductVariant")

        assert updated is not None, f"Price update failed: {response}"
        assert updated.get("price") == price, "Price not updated correctly"

        return updated