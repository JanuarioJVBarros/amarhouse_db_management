from beevo.validation import require_list, require_path


class FacetsAPI:
    def __init__(self, client):
        self.client = client

    def get_facets(self):
        query = """
        query GetFacets($options: FacetListOptions) {
        facets(options: $options) {
            items {
            id
            name
            values {
                id
                name
            }
            }
        }
        }
        """
        response = self.client.request(
            query=query,
            variables={"options": {}},
            operation_name="GetFacets"
        )
        return require_list(
            require_path(response, ["data", "facets", "items"], "get_facets response"),
            "get_facets response.data.facets.items",
        )


    def get_products_by_facet_value(self, facet_value_id):
        query = """
            query Products($input: SearchInput!) {
            search(input: $input) {
                items {
                productName
                productVariantName
                sku
                price {
                    ... on SinglePrice {
                    value
                    }
                }
                }
            }
            }
            """
        
        variables = {
            "input": {
                "facetValueIds": [facet_value_id],
                "groupByProduct": False,
                "take": 1000
            }
        }

        response = self.client.request(
            query=query,
            variables=variables,
            operation_name="Products"
        )

        return require_list(
            require_path(response, ["data", "search", "items"], "get_products_by_facet_value response"),
            "get_products_by_facet_value response.data.search.items",
        )
