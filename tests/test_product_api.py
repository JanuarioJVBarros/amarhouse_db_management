import pytest

from beevo.exceptions import BeevoValidationError
from beevo.product import ProductAPI


class DummyClient:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def request(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


def test_create_product_returns_normalized_product_and_sends_expected_payload():
    client = DummyClient(
        {
            "data": {
                "createProduct": {
                    "id": "prod-1",
                    "name": "Wall Lamp",
                    "slug": "wall-lamp",
                }
            }
        }
    )
    api = ProductAPI(client)

    result = api.create_product(
        {
            "name": "Wall Lamp",
            "slug": "wall-lamp",
            "description": "Short description",
            "description_full": "Long description",
        }
    )

    assert result["id"] == "prod-1"
    request_call = client.calls[0]
    assert request_call["operation_name"] == "CreateProduct"
    assert request_call["variables"]["input"]["translations"][0]["name"] == "Wall Lamp"
    assert request_call["variables"]["input"]["translations"][0]["customFields"]["description_2"] == "Long description"


def test_create_product_raises_when_name_does_not_match():
    client = DummyClient(
        {
            "data": {
                "createProduct": {
                    "id": "prod-1",
                    "name": "Wrong Name",
                    "slug": "wall-lamp",
                }
            }
        }
    )
    api = ProductAPI(client)

    with pytest.raises(BeevoValidationError, match="Product name mismatch"):
        api.create_product({"name": "Wall Lamp", "slug": "wall-lamp"})


def test_create_first_variant_returns_first_variant():
    client = DummyClient(
        {
            "data": {
                "createProductVariants": [
                    {"id": "variant-1", "sku": "WL-1", "price": 1000}
                ]
            }
        }
    )
    api = ProductAPI(client)

    result = api.create_first_variant(
        "prod-1",
        {"name": "Wall Lamp", "sku": "WL-1", "price": 1000},
    )

    assert result == {"id": "variant-1", "sku": "WL-1", "price": 1000}
    assert client.calls[0]["operation_name"] == "CreateProductVariants"


def test_create_first_variant_raises_when_list_is_empty():
    client = DummyClient({"data": {"createProductVariants": []}})
    api = ProductAPI(client)

    with pytest.raises(BeevoValidationError, match="Variant creation returned an empty list"):
        api.create_first_variant("prod-1", {"name": "Wall Lamp"})


def test_get_by_slug_returns_first_match_or_none():
    client = DummyClient(
        {
            "data": {
                "products": {
                    "items": [
                        {"id": "prod-1", "name": "Wall Lamp", "slug": "wall-lamp"}
                    ]
                }
            }
        }
    )
    api = ProductAPI(client)

    assert api.get_by_slug("wall-lamp") == {"id": "prod-1", "name": "Wall Lamp", "slug": "wall-lamp"}

    client.response = {"data": {"products": {"items": []}}}
    assert api.get_by_slug("missing") is None


def test_update_sku_and_update_price_validate_updated_values():
    client = DummyClient({"data": {"updateProductVariant": {"id": "variant-1", "sku": "WL-2"}}})
    api = ProductAPI(client)

    updated_sku = api.update_sku("variant-1", "WL-2")
    assert updated_sku["sku"] == "WL-2"

    client.response = {"data": {"updateProductVariant": {"id": "variant-1", "price": 1200}}}
    updated_price = api.update_price("variant-1", 1200)
    assert updated_price["price"] == 1200


def test_update_sku_and_update_price_raise_for_mismatched_values():
    client = DummyClient({"data": {"updateProductVariant": {"id": "variant-1", "sku": "WRONG"}}})
    api = ProductAPI(client)

    with pytest.raises(BeevoValidationError, match="SKU not updated correctly"):
        api.update_sku("variant-1", "WL-2")

    client.response = {"data": {"updateProductVariant": {"id": "variant-1", "price": 999}}}
    with pytest.raises(BeevoValidationError, match="Price not updated correctly"):
        api.update_price("variant-1", 1200)
