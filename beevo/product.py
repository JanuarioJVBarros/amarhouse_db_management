class ProductAPI:
    def __init__(self, client):
        self.client = client

    def create_product(self, name, slug, language="pt_PT"):
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
                "translations": [
                    {
                        "languageCode": language,
                        "name": name,
                        "slug": slug
                    }
                ]
            }
        }

        return self.client.request(
            query=query,
            variables=variables,
            operation_name="CreateProduct"
        )