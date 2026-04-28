from openpyxl import Workbook

from beevo.client import BeevoClient
from beevo.config.env_loader import load_environment
from beevo.variants import VariantsAPI
from scripts.update_prices import load_prices_from_excel


def find_missing_skus(price_map, variant_lookup):
    missing = []

    for sku, price in sorted(price_map.items()):
        normalized_sku = sku.strip().upper()
        if normalized_sku in variant_lookup:
            continue

        missing.append(
            {
                "sku": normalized_sku,
                "price": price,
            }
        )

    return missing


def export_missing_to_excel(missing_items, filename="missing_products.xlsx"):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Missing Products"
    sheet.append(["SKU", "Price"])

    for item in missing_items:
        sheet.append([item["sku"], item["price"]])

    workbook.save(filename)


def run_missing_products_report(excel_file, output_file="missing_products.xlsx"):
    settings = load_environment()
    print("Environment loaded. Starting missing product comparison...")
    print(f"Using Beevo URL: {settings.beevo_url}")

    client = BeevoClient(
        settings.beevo_url,
        settings.beevo_cookie,
        timeout=settings.request_timeout,
    )
    variants_api = VariantsAPI(client)

    price_map = load_prices_from_excel(excel_file)
    variant_lookup = variants_api.build_variant_lookup()
    missing_items = find_missing_skus(price_map, variant_lookup)

    if not missing_items:
        print("[OK] No missing products found")
        return missing_items

    export_missing_to_excel(missing_items, filename=output_file)
    print(f"[OK] Found {len(missing_items)} missing products")
    print(f"[OK] Report saved to {output_file}")
    return missing_items


if __name__ == "__main__":
    run_missing_products_report("TABELA-ISG.xlsx")
