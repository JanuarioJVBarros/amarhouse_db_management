import json
from types import SimpleNamespace
import time

from beevo.client import BeevoClient
from core.publisher import ProductPublisher
from utils import json_utils


def build_acabamentos_option_group(product_json):
    """
    Flattens ALL acabamento groups into ONE single group:
    "Acabamentos"
    """

    acabamentos_options = []
    cor_options = []
    final_options = []
    for group_name, group_options in product_json.get("acabamentos", {}).items():
        acabamentos_options.append(group_name.capitalize())
        for option in group_options:

            # Ensure format consistency
            option = option.strip()
            cor_options.append(option)

    final_options.append({"name": "Acabamentos", "options": acabamentos_options})
    final_options.append({"name": "Cor", "options": cor_options})

    return final_options


def build_variants(product_json):
    variants = []

    for acabamento, options in product_json.get("acabamentos", {}).items():
        for option in options:

            option = option.strip()

            if "(" not in option:
                continue

            # extrair código (ex: BR)
            code = option.split("(")[-1].replace(")", "").strip()


            variants.append({
                "name": f"{product_json['name']} - {acabamento.capitalize()} {option}",
                "sku": f"{product_json['reference']}{code}",

                "options": {
                    "Acabamento": acabamento.capitalize(),
                    "Cor": option
                },

                "price": 0
            })

    return variants


def load_and_prepare_products(file_path):

    def make_slug(name):
        return name.lower().replace(" ", "-").replace("/", "-")

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    prepared = []

    for p in data["products"]:
        product = SimpleNamespace(**p)

        product.slug = make_slug(p["name"])

        # ✅ FIXED STRUCTURE
        product.option_groups = build_acabamentos_option_group(p)

        # Variants aligned with flattened options
        product.variants = build_variants(p)

        prepared.append(product)

    return prepared

if __name__ == "__main__":
    client = BeevoClient()
    publisher = ProductPublisher(client)

    scraped_products = load_and_prepare_products("espelhos_acabamentos.json")
    print(scraped_products)

    #exit(0)
    #scraped_products = json_utils.load_json("output copy.json")

    print("\n=== PUBLISH RESULT ===")

    for product in scraped_products:
        #product = SimpleNamespace(**product)
        result = publisher.publish(product)
        time.sleep(1)