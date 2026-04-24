from beevo.exceptions import BeevoValidationError
from beevo.validation import require_mapping, require_path


class OptionsAPI:
    def __init__(self, client):
        self.client = client

    def _build_option_payload(self, option, language):
        if isinstance(option, dict):
            name = option.get("name")
            code = option.get("code") or str(name).strip().lower()
        else:
            name = str(option).strip()
            code = name.lower()

        if not name:
            raise BeevoValidationError("Option name cannot be empty")

        return {
            "code": code,
            "translations": [
                {
                    "languageCode": language,
                    "name": name
                }
            ]
        }

    # -------------------------
    # CREATE OPTION GROUP
    # -------------------------
    def create_option_group(
        self,
        name,
        options,
        code=None,
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

        if not name:
            raise BeevoValidationError("Option group name cannot be empty")

        options_list = [self._build_option_payload(element, language) for element in options]

        variables = {
            "input": {
                "code": code or name.lower(),
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
        created_group = require_mapping(
            require_path(response, ["data", "createProductOptionGroup"], "create_option_group response"),
            "create_option_group response.data.createProductOptionGroup",
        )

        if created_group.get("name") != name:
            raise BeevoValidationError(
                f"Name mismatch: expected {name}, got {created_group.get('name')}"
            )

        if "id" not in created_group:
            raise BeevoValidationError("Missing option group ID")

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
        result = require_mapping(
            require_path(response, ["data", "addOptionGroupToProduct"], "add_option_group_to_product response"),
            "add_option_group_to_product response.data.addOptionGroupToProduct",
        )

        if result.get("id") != product_id:
            raise BeevoValidationError(
                f"Product ID mismatch: expected {product_id}, got {result.get('id')}"
            )

        if "optionGroups" not in result:
            raise BeevoValidationError("Missing optionGroups field")

        return result
