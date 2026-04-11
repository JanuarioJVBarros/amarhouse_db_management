class VariantsAPI:
    def __init__(self, client):
        self.client = client

    def create_variant(self, product_id, sku, price, stock, option_ids, language="pt_PT"):
        """
        Creates a product variant linked to a product + options.
        
        - product_id: ID of the product
        - sku: stock keeping unit
        - price: numeric price
        - stock: initial stock
        - option_ids: list of option IDs (e.g. ["2000k-id"])
        """

        query = """
        mutation CreateProductVariant($input: CreateProductVariantInput!) {
          createProductVariant(input: $input) {
            id
            sku
            price
            stockOnHand
          }
        }
        """

        variables = {
            "input": {
                "productId": product_id,
                "sku": sku,
                "price": price,
                "stockOnHand": stock,
                "enabled": True,
                "optionIds": option_ids
            }
        }

        return self.client.request(
            query=query,
            variables=variables,
            operation_name="CreateProductVariant"
        )