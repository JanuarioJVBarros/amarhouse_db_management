class OptionsAPI:
    def __init__(self, client):
        self.client = client

    def create_option_group(self, code, name, options, language="pt_PT"):
        query = """
        mutation CreateProductOptionGroup($input: CreateProductOptionGroupInput!) {
          createProductOptionGroup(input: $input) {
            id
            code
            name
          }
        }
        """

        variables = {
            "input": {
                "code": code,
                "translations": [
                    {
                        "languageCode": language,
                        "name": name
                    }
                ],
                "options": [
                    {
                        "code": opt["code"],
                        "translations": [
                            {
                                "languageCode": language,
                                "name": opt["name"]
                            }
                        ]
                    }
                    for opt in options
                ]
            }
        }

        return self.client.request(
            query=query,
            variables=variables,
            operation_name="CreateProductOptionGroup"
        )

    def add_option_group_to_product(self, product_id, option_group_id):
        query = """
        mutation AddOptionGroupToProduct($productId: ID!, $optionGroupId: ID!) {
          addOptionGroupToProduct(productId: $productId, optionGroupId: $optionGroupId) {
            id
          }
        }
        """

        variables = {
            "productId": product_id,
            "optionGroupId": option_group_id
        }

        return self.client.request(
            query=query,
            variables=variables,
            operation_name="AddOptionGroupToProduct"
        )