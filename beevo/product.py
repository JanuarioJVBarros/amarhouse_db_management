import json

class ProductAPI:
    def __init__(self, client):
        self.client = client

class ProductAPI:
    def __init__(self, client):
        self.client = client

    def create_product(self, product_data):
        """
        Creates a product in Beevo CMS using GraphQL.
        Fully dynamic via variables (no hardcoded query values).
        """

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

        return self.client.request(
            query=query,
            variables=variables,
            operation_name="CreateProduct",
        )
    
    
    def create_first_variant(self, product_id, product_data):
        query = """
                mutation CreateProductVariants($input: [CreateProductVariantInput!]!) {
                createProductVariants(input: $input) {
                    ...ProductVariant
                    __typename
                }
                }

                fragment ProductVariant on ProductVariant {
                id
                createdAt
                updatedAt
                enabled
                languageCode
                name
                price
                currencyCode
                priceWithTax
                stockOnHand
                stockAllocated
                trackInventory
                outOfStockThreshold
                useGlobalOutOfStockThreshold
                taxRateApplied {
                    id
                    name
                    value
                    __typename
                }
                taxCategory {
                    id
                    name
                    __typename
                }
                sku
                options {
                    ...ProductOption
                    __typename
                }
                facetValues {
                    id
                    code
                    name
                    facet {
                    id
                    name
                    __typename
                    }
                    __typename
                }
                featuredAsset {
                    ...Asset
                    __typename
                }
                assets {
                    ...Asset
                    __typename
                }
                translations {
                    id
                    languageCode
                    name
                    __typename
                }
                channels {
                    id
                    code
                    __typename
                }
                customFields {
                    weight
                    pvp
                    ean
                    __typename
                }
                __typename
                }

                fragment ProductOption on ProductOption {
                id
                createdAt
                updatedAt
                code
                languageCode
                name
                groupId
                translations {
                    id
                    languageCode
                    name
                    __typename
                }
                __typename
                }

                fragment Asset on Asset {
                id
                createdAt
                updatedAt
                name
                fileSize
                mimeType
                type
                preview
                source
                width
                height
                focalPoint {
                    x
                    y
                    __typename
                }
                __typename
                }
                """
        
        variables = {
            "input": [
                {
                    "productId": product_id,
                    "price": product_data.get("price", 0),
                    "sku": product_data.get("sku", 0),
                    "translations": [
                        {
                            "languageCode": "pt_PT",
                            "name": product_data.get("name", 0)
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

        return self.client.request(
            query=query,
            variables=variables,
            operation_name="CreateProductVariants",
        )

    def get_by_slug(self, slug, language="pt_PT"):
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

        result = self.client.request(
            query=query,
            variables=variables,
            operation_name="GetProducts"
        )
        
        items = result.get("data",[]).get("products", {}).get("items", [])
        return items[0] if items else None
    
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

    def update_sku(self, variant_id, sku):
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

        return self.client.request(
            query=query,
            variables=variables,
            operation_name="UpdateProductVariant"
        )

            
    def update_price(self, variant_id, price, currency="EUR"):
        query = """
            mutation UpdateProductVariant($input: UpdateProductVariantInput!) {
            updateProductVariant(input: $input) {
                id
                sku
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

        return self.client.request(
            query=query,
            variables=variables,
            operation_name="UpdateProductVariant"
        )

