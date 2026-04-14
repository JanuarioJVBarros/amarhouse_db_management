from utils import json_utils
import pandas as pd
from pathlib import Path

# TODO: Hard_coded, make it dynamic
JSON_PATH = Path("scraped_products copy.json")
EXCEL_PATH = Path("Tabela_Golmar_PVP_2026.xlsx")

CODE_COLUMN = "CÓDIGO"
PRICE_COLUMN = "preço loja+20"

def load_price_dict(excel_path):
    df = pd.read_excel(excel_path)

    # clean column names (important for accents / spaces)
    df.columns = df.columns.str.strip()

    price_dict = {}

    for _, row in df.iterrows():
        code = str(row.get(CODE_COLUMN)).strip()

        if not code or code == "nan":
            continue

        price = row.get(PRICE_COLUMN)

        if pd.isna(price):
            continue

        price_dict[code] = float(price)

    return price_dict

def update_prices(products, price_map):
    updated = 0
    missing = 0

    for product in products:
        # add a G befor the sku to match the code in the excel prices
        sku = product.get("sku")
        code = f"G{sku}"

        if not code:
            continue

        code = code.strip()

        if code in price_map:
            # beevo website does not consider the decimal cases
            product["price"] = int(round(price_map[code], 2) * 100)
            updated += 1
        else:
            product["price"] = 0
            missing += 1

    print(f"✅ Updated: {updated}")
    print(f"⚠️ Missing in Excel: {missing}")

    return products

# -------------------------
# MAIN
# -------------------------
def main():
    print("Loading JSON...")
    products = json_utils.load_json(JSON_PATH)

    print("Loading Excel...")
    price_map = load_price_dict(EXCEL_PATH)

    print(f"Loaded {len(price_map)} prices")

    print("Updating products...")
    updated_products = update_prices(products, price_map)

    print("Saving...")
    json_utils.save_json(JSON_PATH, updated_products)

    print("Done ✅")


if __name__ == "__main__":
    main()