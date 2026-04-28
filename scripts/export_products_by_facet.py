from pathlib import Path
import argparse

import openpyxl

from beevo.client import BeevoClient
from beevo.config.env_loader import load_environment
from beevo.facets import FacetsAPI


def format_price(price_data):
    if not price_data or price_data.get("value") is None:
        return None
    return f"{price_data['value'] / 100:.2f} EUR"


def collect_products_by_facet_name(facets_api, facet_name):
    facets = facets_api.get_facets()
    matching_facet = next((facet for facet in facets if facet["name"] == facet_name), None)

    if not matching_facet:
        raise ValueError(f"Facet '{facet_name}' not found")

    exported = []
    for value in matching_facet.get("values", []):
        facet_value_id = value.get("id")
        facet_value_name = value.get("name")
        print(f"[STEP] Fetching products for facet value: {facet_value_name} ({facet_value_id})")

        seen_skus = set()
        items = []
        for product in facets_api.get_products_by_facet_value(facet_value_id):
            sku = (product.get("sku") or "").strip()
            if not sku or sku in seen_skus:
                continue

            seen_skus.add(sku)
            items.append(
                {
                    "sku": sku,
                    "name": product.get("productVariantName") or product.get("productName"),
                    "price": format_price(product.get("price")),
                }
            )

        exported.append(
            {
                "facet_value_id": facet_value_id,
                "facet_value_name": facet_value_name,
                "products": items,
            }
        )

    return exported


def export_to_excel(products, filename):
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Products"
    sheet.append(["SKU", "Name", "Price"])

    for product in products:
        sheet.append([product.get("sku") or "N/A", product.get("name"), product.get("price")])

    workbook.save(filename)


def export_products_for_facet(facet_name, output_dir="."):
    settings = load_environment()
    print("Environment loaded. Starting data collection...")
    print(f"Using Beevo URL: {settings.beevo_url}")

    client = BeevoClient(
        settings.beevo_url,
        settings.beevo_cookie,
        timeout=settings.request_timeout,
    )
    facets_api = FacetsAPI(client)
    groups = collect_products_by_facet_name(facets_api, facet_name)

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    for group in groups:
        filename = output_path / f"{facet_name}_{group['facet_value_id']}_products.xlsx"
        export_to_excel(group["products"], filename)
        print(
            f"[OK] Exported {len(group['products'])} products for "
            f"{group['facet_value_name']} to {filename}"
        )

    return groups


def main(argv=None):
    parser = argparse.ArgumentParser(description="Export Beevo products by facet value.")
    parser.add_argument("--facet-name", default="Marcas", help="Facet name to export.")
    parser.add_argument("--output-dir", default=".", help="Directory for the exported files.")
    args = parser.parse_args(argv)
    return export_products_for_facet(args.facet_name, output_dir=args.output_dir)


if __name__ == "__main__":
    main()
