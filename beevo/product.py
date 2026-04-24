from beevo.exceptions import BeevoValidationError
from beevo.validation import require_list, require_mapping, require_path


class ProductAPI:
    def __init__(self, client):
        self.client = client


    def create_product(self, product_data, expected_status=200):
        product_data = require_mapping(product_data, "product_data")
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

        product = require_mapping(
            require_path(response, ["data", "createProduct"], "create_product response"),
            "create_product response.data.createProduct",
        )

        if not product.get("id"):
            raise BeevoValidationError("Product creation response is missing product id")

        if product.get("name") != product_data.get("name"):
            raise BeevoValidationError("Product name mismatch after creation")

        return product


    def create_first_variant(self, product_id, product_data, expected_status=200):
        product_data = require_mapping(product_data, "product_data")
        query = """
        mutation CreateProductVariants($input: [CreateProductVariantInput!]!) {
            createProductVariants(input: $input) {
                id
                sku
                price
            }
        }
        """

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

        variants = require_list(
            require_path(response, ["data", "createProductVariants"], "create_first_variant response"),
            "create_first_variant response.data.createProductVariants",
        )

        if not variants:
            raise BeevoValidationError("Variant creation returned an empty list")

        return require_mapping(variants[0], "create_first_variant first variant")


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

        items = require_list(
            require_path(response, ["data", "products", "items"], "get_by_slug response"),
            "get_by_slug response.data.products.items",
        )

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

        updated = require_mapping(
            require_path(response, ["data", "updateProductVariant"], "update_sku response"),
            "update_sku response.data.updateProductVariant",
        )

        if updated.get("sku") != sku:
            raise BeevoValidationError("SKU not updated correctly")

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

        updated = require_mapping(
            require_path(response, ["data", "updateProductVariant"], "update_price response"),
            "update_price response.data.updateProductVariant",
        )

        if updated.get("price") != price:
            raise BeevoValidationError("Price not updated correctly")

        return updated
