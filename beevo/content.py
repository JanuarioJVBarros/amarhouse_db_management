class ContentAPI:
    def __init__(self, client):
        self.client = client

    def update_product_content(
        self,
        product_id,
        translation_id,
        name,
        slug,
        description,
        description_full="",
        other_information="",
        featured=False,
        main_collection_id=None,
        related_products_ids=None,
        google_id_id=None,
        language="pt_PT"
    ):
        query = """
        mutation UpdateProduct($input: UpdateProductInput!) {
          updateProduct(input: $input) {
            id
            name
            slug
          }
        }
        """

        variables = {
            "input": {
                "id": product_id,
                "enabled": True,
                "translations": [
                    {
                        "id": translation_id,
                        "languageCode": language,
                        "name": name,
                        "slug": slug,
                        "description": description,
                        "customFields": {
                            "description_2": description_full,
                            "other_information": other_information
                        }
                    }
                ],
                "customFields": {
                    "featured": featured,
                    "mainCollectionId": main_collection_id,
                    "relatedProductsIds": related_products_ids or [],
                    "googleIdId": google_id_id
                }
            }
        }

        return self.client.request(
            query=query,
            variables=variables,
            operation_name="UpdateProduct"
        )