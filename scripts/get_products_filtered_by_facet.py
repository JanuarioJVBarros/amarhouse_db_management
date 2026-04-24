from beevo.client import BeevoClient
from beevo.facets import FacetsAPI
from beevo.config.config import BEEVO_URL, BEEVO_COOKIE
from beevo.config.env_loader import load_environment
import openpyxl
import os

# =========================
# DATA PROCESSING
# =========================

def collect_products_by_facet_name(facets_api, facet_name):
    facets = facets_api.get_facets()

    # find the target facet
    facet_id_list = []
    for facet in facets:
        if facet["name"] == facet_name:
            facet_values = facet["values"]
            print(f"Found facet '{facet_name}' with {len(facet_values)} values")
            for value in facet_values:
                print(f" - {value['name']} (ID: {value['id']})")
                facet_id_list.append(value.get("id"))

    print(facet_id_list)
    if not facet_id_list:
        raise ValueError(f"Facet '{facet_name}' not found")

    final_products = []
    for facet_id in facet_id_list:
        print(f"Using facet: {facet_id}")

        products_map = {}

        print(f"Fetching products for facet value: {facet_id}")

        items = facets_api.get_products_by_facet_value(facet_id)

        final_facet_products = []
        for p in items:
            sku = p.get("sku")
            print(f"Processing product with SKU: {sku}")
            if not sku:
                continue

            if sku in products_map:
                continue

            # price handling
            price_value = None
            price_data = p.get("price")

            if price_data and price_data.get("value") is not None:
                price_value = f"{price_data['value'] / 100:.2f} €"

            products_map = {
                "sku": sku,
                "name": p.get("productVariantName") or p.get("productName"),
                "price": price_value
            }
            
            final_facet_products.append(products_map)
        final_products.append({facet_id: final_facet_products})
        

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

    for product in products:
        for p in product:
            print(f"Exporting product: {p['sku']} - {p['name']} - {p['price']}")
            ws.append([
                p["sku"] or "N/A",
                p["name"],
                p["price"]
            ])

    wb.save(filename)


# =========================
# MAIN
# =========================
if __name__ == "__main__":
    load_environment()
    BEEVO_URL = os.getenv("BEEVO_URL")
    BEEVO_COOKIE = os.getenv("BEEVO_COOKIE")
    print("Environment loaded. Starting data collection...")
    print(f"Using Beevo URL: {BEEVO_URL}")
    print(f"Using Beevo Cookie: {BEEVO_COOKIE}")
    client = BeevoClient(BEEVO_URL, BEEVO_COOKIE)
    facets_api = FacetsAPI(client)

    facet_name = "Marcas"
    products = collect_products_by_facet_name(facets_api, facet_name)

    for product in products:
        for facet_id, product_data in product.items():
            print(f"Facet ID: {facet_id} - Products: {len(product_data)}")
            export_to_excel([product_data], filename=f"{facet_name}_{facet_id}_products.xlsx")

    print(f"Exported {len(products)} products")