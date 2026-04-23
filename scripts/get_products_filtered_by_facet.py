from beevo.client import BeevoClient
import openpyxl

GET_FACETS_QUERY = """
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

PRODUCTS_QUERY = """
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


# =========================
# API METHODS
# =========================

def get_facets(client):
    response = client.request(
        GET_FACETS_QUERY,
        variables={"options": {}},
        operation_name="GetFacets"
    )
    return response["data"]["facets"]["items"]


def get_products_by_facet_value(client, facet_value_id):
    variables = {
        "input": {
            "facetValueIds": [facet_value_id],
            "groupByProduct": False,
            "take": 1000
        }
    }

    response = client.request(
        PRODUCTS_QUERY,
        variables=variables,
        operation_name="Products"
    )

    return response["data"]["search"]["items"]


# =========================
# DATA PROCESSING
# =========================

def collect_products_by_facet_name(client, facet_name):
    facets = get_facets(client)

    # find the target facet
    facet_id_list = []
    for facet in facets:
        if facet["name"] == facet_name:
            facet_values = facet["values"]
            for value in facet_values:
                if value["name"] == facet_name:
                    facet_id_list.append(value.get("id"))

    if not facet_id_list:
        raise ValueError(f"Facet '{facet_name}' not found")

    final_products = []
    for target_facet_id in facet_id_list:
        print(f"Using facet: {target_facet_id} - {facet_name}")

        products_map = {}

        print(f"Fetching products for facet value: {facet_name}")

        items = get_products_by_facet_value(client, target_facet_id)

        for p in items:
            sku = p.get("sku")
            if not sku:
                continue

            if sku in products_map:
                continue

            # price handling
            price_value = None
            price_data = p.get("price")

            if price_data and price_data.get("value") is not None:
                price_value = f"{price_data['value'] / 100:.2f} €"

            products_map[sku] = {
                "sku": sku,
                "name": p.get("productVariantName") or p.get("productName"),
                "price": price_value
            }
            
        final_products.append({target_facet_id: products_map[sku]})

    return final_products

# =========================
# EXPORT
# =========================

def export_to_excel(products, filename="products.xlsx"):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Products"

    # headers
    ws.append(["SKU", "Name", "Price"])

    for p in products:
        ws.append([
            p["sku"],
            p["name"],
            p["price"]
        ])

    wb.save(filename)


# =========================
# MAIN
# =========================
if __name__ == "__main__":
    client = BeevoClient()

    facet_name = "Marcas"
    products = collect_products_by_facet_name(client, facet_name)

    for product in products:
        for facet_id, product_data in product.items():
            print(f"Facet ID: {facet_id} - Products: {len(product_data)}")
            export_to_excel([product_data], filename=f"{facet_name}_{facet_id}_products.xlsx")

    print(f"Exported {len(products)} products")