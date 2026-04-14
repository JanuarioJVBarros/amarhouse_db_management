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

        return self.client.request(
            query=query,
            variables=variables,
            operation_name="GetFacetValueList"
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

        return self.client.request(
            query=query,
            variables=variables,
            operation_name="UpdateProduct"
        )