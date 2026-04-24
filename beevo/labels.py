from beevo.validation import require_list, require_mapping, require_path


class LabelsAPI:
    def __init__(self, client):
        self.client = client

    def get_facet_values(self, ids):
        query = """
        query GetFacetValueList($options: FacetValueListOptions) {
          facetValues(options: $options) {
            items {
              id
              name
              code
            }
          }
        }
        """

        variables = {
            "options": {
                "filter": {
                    "id": {
                        "in": ids
                    }
                }
            }
        }

        response = self.client.request(
            query=query,
            variables=variables,
            operation_name="GetFacetValueList"
        )

        return require_list(
            require_path(response, ["data", "facetValues", "items"], "get_facet_values response"),
            "get_facet_values response.data.facetValues.items",
        )
    
    def add_labels_to_product(self, product_id, facet_value_ids):
        query = """
            mutation UpdateProduct($input: UpdateProductInput!) {
                updateProduct(input: $input) {
                    id
                }
                }
        """

        variables = {
            "input": {
                "id": product_id,
                "facetValueIds": facet_value_ids
            }
        }

        response = self.client.request(
            query=query,
            variables=variables,
            operation_name="UpdateProduct"
        )

        return require_mapping(
            require_path(response, ["data", "updateProduct"], "add_labels_to_product response"),
            "add_labels_to_product response.data.updateProduct",
        )
