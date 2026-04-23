from scrapers.efapel.options_code import COLOR_MAP


class OptionsAPI:
    def __init__(self, client):
        self.client = client

    def create_option_group(self, name, options, language="pt_PT"):
        query = """
            mutation CreateProductOptionGroup($input: CreateProductOptionGroupInput!) {
            createProductOptionGroup(input: $input) {
                id
                code
                name
                options {
                id
                code
                name
                }
            }
            }
        """
        
        options_list = [{"code": element.lower(), "translations": [{"languageCode": language, "name": element}]} for element in options]
        variables = {
            "input": {
                "code": name.lower(),
                "translations": [
                {
                    "languageCode": language,
                    "name": name
                }
                ],
                "options": options_list
            }
            }

        return self.client.request(
            query=query,
            variables=variables,
            operation_name="CreateProductOptionGroup"
        )

    def add_option_group_to_product(self, product_id: str, option_group_id: str):
        query = """
        mutation AddOptionGroupToProduct($productId: ID!, $optionGroupId: ID!) {
            addOptionGroupToProduct(productId: $productId, optionGroupId: $optionGroupId) {
                id
                name
                optionGroups {
                    id
                    code
                }
            }
        }
        """

        variables = {
            "productId": product_id,
            "optionGroupId": option_group_id
        }

        response =  self.client.request(query=query,variables=variables,operation_name="AddOptionGroupToProduct")

        # Error handling
        if "errors" in response:
            raise Exception(f"GraphQL Error: {response['errors']}")

        data = response.get("data", {}).get("addOptionGroupToProduct")
        if not data:
            raise Exception("Failed to add option group to product")