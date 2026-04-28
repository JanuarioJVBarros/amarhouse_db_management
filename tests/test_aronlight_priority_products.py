from scrapers.aronlight.publish_priority_products import build_all_priority_products


def test_build_all_priority_products_generates_expected_manual_seed_shape():
    products = build_all_priority_products()

    assert len(products) == 15

    board = next(product for product in products if product.name == "BOARD SURFACE")
    assert board.facet_value_ids == ["164"]
    assert board.option_groups == [
        {
            "name": "Referencia",
            "options": ["ILAR-03671", "ILAR-03670", "ILAR-02945"],
        }
    ]
    assert board.variants[0]["options"] == {"Referencia": "ILAR-03671"}

    novva = next(product for product in products if product.name == "NOVVA")
    assert novva.option_groups == []
    assert novva.variants == [
        {
            "name": "NOVVA ILAR-03759",
            "sku": "ILAR-03759",
            "price": 0,
            "options": {},
        }
    ]
