class OptionsAPI:
    def __init__(self, client):
        self.client = client

    # -------------------------
    # CREATE OPTION GROUP
    # -------------------------
    def create_option_group(
        self,
        name,
        options,
        language="pt_PT",
        expected_status=200
    ):
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

        options_list = [
            {
                "code": element.lower(),
                "translations": [
                    {
                        "languageCode": language,
                        "name": element
                    }
                ]
            }
            for element in options
        ]

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

        response = self.client.request(
            query=query,
            variables=variables,
            operation_name="CreateProductOptionGroup",
            expected_status=expected_status
        )

        # -------------------------
        # VALIDATION LAYER
        # -------------------------
        created_group = response.get("data", {}).get("createProductOptionGroup")

        assert created_group is not None, (
            f"Option group creation failed. Full response:\n{response}"
        )

        assert created_group.get("name") == name, (
            f"Name mismatch: expected {name}, got {created_group.get('name')}"
        )

        assert "id" in created_group, "Missing option group ID"

        return created_group

    # -------------------------
    # ADD OPTION GROUP TO PRODUCT
    # -------------------------
    def add_option_group_to_product(
        self,
        product_id: str,
        option_group_id: str,
        expected_status=200
    ):
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

        response = self.client.request(
            query=query,
            variables=variables,
            operation_name="AddOptionGroupToProduct",
            expected_status=expected_status
        )

        # -------------------------
        # VALIDATION LAYER
        # -------------------------
        result = response.get("data", {}).get("addOptionGroupToProduct")

        assert result is not None, (
            f"Failed to add option group to product. Response:\n{response}"
        )

        assert result.get("id") == product_id, (
            f"Product ID mismatch: expected {product_id}, got {result.get('id')}"
        )

        assert "optionGroups" in result, "Missing optionGroups field"

        return result