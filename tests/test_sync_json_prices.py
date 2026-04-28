from argparse import Namespace

from openpyxl import Workbook

from scripts.export_products_by_facet import collect_products_by_facet_name
from scripts.sync_json_prices_from_excel import (
    load_price_dict,
    resolve_args,
    update_product_prices,
    update_variant_prices,
)


class StubFacetsAPI:
    def get_facets(self):
        return [
            {
                "name": "Marcas",
                "values": [
                    {"id": "facet-1", "name": "Ecolux"},
                    {"id": "facet-2", "name": "Golmar"},
                ],
            }
        ]

    def get_products_by_facet_value(self, facet_value_id):
        if facet_value_id == "facet-1":
            return [
                {
                    "sku": "A1",
                    "productName": "Alpha",
                    "price": {"value": 1000},
                },
                {
                    "sku": "A1",
                    "productName": "Alpha Duplicate",
                    "price": {"value": 1000},
                },
            ]

        return [
            {
                "sku": "B2",
                "productVariantName": "Beta Variant",
                "productName": "Beta",
                "price": {"value": 2500},
            }
        ]


def test_load_price_dict_normalizes_headers(tmp_path):
    file_path = tmp_path / "prices.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["REFERÊNCIA", "PREÇO LOJA +20%"])
    sheet.append(["ABC-1", 12.5])
    workbook.save(file_path)

    result = load_price_dict(file_path, "REFERENCIA", "PRECO LOJA +20%")

    assert result == {"ABC-1": 12.5}


def test_update_variant_prices_updates_variant_entries():
    products = [{"variants": [{"sku": "ABC-1", "price": 0}, {"sku": "MISS", "price": 0}]}]

    updated, missing = update_variant_prices(products, {"ABC-1": 12.34})

    assert updated == 1
    assert missing == 1
    assert products[0]["variants"][0]["price"] == 1234
    assert products[0]["variants"][1]["price"] == 0


def test_update_product_prices_applies_prefix():
    products = [{"sku": "123", "price": 0}, {"sku": "999", "price": 0}]

    updated, missing = update_product_prices(products, {"G123": 8.5}, sku_prefix="G")

    assert updated == 1
    assert missing == 1
    assert products[0]["price"] == 850
    assert products[1]["price"] == 0


def test_resolve_args_uses_profile_defaults():
    args = Namespace(
        profile="golmar",
        json_file=None,
        excel_file=None,
        code_column=None,
        price_column=None,
        target=None,
        sku_prefix=None,
    )

    resolved = resolve_args(args)

    assert resolved["target"] == "products"
    assert resolved["sku_prefix"] == "G"
    assert resolved["excel_path"] == "Tabela_Golmar_PVP_2026.xlsx"


def test_collect_products_by_facet_name_groups_and_deduplicates():
    result = collect_products_by_facet_name(StubFacetsAPI(), "Marcas")

    assert result == [
        {
            "facet_value_id": "facet-1",
            "facet_value_name": "Ecolux",
            "products": [{"sku": "A1", "name": "Alpha", "price": "10.00 EUR"}],
        },
        {
            "facet_value_id": "facet-2",
            "facet_value_name": "Golmar",
            "products": [{"sku": "B2", "name": "Beta Variant", "price": "25.00 EUR"}],
        },
    ]
