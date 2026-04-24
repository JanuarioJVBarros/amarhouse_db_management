import pytest

from beevo.exceptions import BeevoValidationError
from beevo.variants import VariantsAPI


class DummyClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def request(self, **kwargs):
        self.calls.append(kwargs)
        if not self.responses:
            raise AssertionError("No more responses configured")
        return self.responses.pop(0)


def test_create_variant_returns_first_created_variant_and_sends_expected_payload():
    client = DummyClient(
        [
            {
                "data": {
                    "createProductVariants": [
                        {"id": "variant-1", "sku": "WL-1", "price": 1000}
                    ]
                }
            }
        ]
    )
    api = VariantsAPI(client)

    result = api.create_variant(
        product_id="prod-1",
        name="Wall Lamp",
        sku="WL-1",
        price=1000,
        stock=5,
        option_ids=["opt-1"],
    )

    assert result["id"] == "variant-1"
    request_call = client.calls[0]
    assert request_call["operation_name"] == "CreateProductVariants"
    assert request_call["variables"]["input"][0]["stockLevels"][0]["stockOnHand"] == 5
    assert request_call["variables"]["input"][0]["optionIds"] == ["opt-1"]


def test_create_variant_raises_for_mismatched_response():
    client = DummyClient(
        [{"data": {"createProductVariants": [{"id": "variant-1", "sku": "WRONG", "price": 999}]}}]
    )
    api = VariantsAPI(client)

    with pytest.raises(BeevoValidationError, match="SKU mismatch after creation"):
        api.create_variant(
            product_id="prod-1",
            name="Wall Lamp",
            sku="WL-1",
            price=1000,
            stock=5,
            option_ids=[],
        )


def test_get_product_variants_by_sku_and_get_variant_by_sku():
    client = DummyClient(
        [
            {"data": {"productVariants": {"items": [{"id": "variant-1", "sku": "WL-1", "price": 1000}]}}},
            {"data": {"productVariants": {"items": []}}},
        ]
    )
    api = VariantsAPI(client)

    items = api.get_product_variants_by_sku("WL-1")
    assert items == [{"id": "variant-1", "sku": "WL-1", "price": 1000}]

    assert api.get_variant_by_sku("missing") is None


def test_get_all_variants_paginates_until_total_items_reached(capsys):
    client = DummyClient(
        [
            {"data": {"productVariants": {"items": [{"id": "1", "sku": "A", "price": 100}], "totalItems": 2}}},
            {"data": {"productVariants": {"items": [{"id": "2", "sku": "B", "price": 200}], "totalItems": 2}}},
        ]
    )
    api = VariantsAPI(client)

    result = api.get_all_variants()

    assert result == [
        {"id": "1", "sku": "A", "price": 100},
        {"id": "2", "sku": "B", "price": 200},
    ]
    assert len(client.calls) == 2
    output = capsys.readouterr().out
    assert "[FETCH] 1/2" in output
    assert "[FETCH] 2/2" in output


def test_get_all_variants_raises_when_total_items_is_invalid():
    client = DummyClient(
        [{"data": {"productVariants": {"items": [], "totalItems": "two"}}}]
    )
    api = VariantsAPI(client)

    with pytest.raises(BeevoValidationError, match="totalItems must be an integer"):
        api.get_all_variants()


def test_build_variant_lookup_normalizes_sku_keys_and_skips_empty_values(capsys):
    client = DummyClient([])
    api = VariantsAPI(client)
    api.get_all_variants = lambda: [
        {"id": "1", "sku": " abc-1 ", "price": 100},
        {"id": "2", "sku": None, "price": 200},
    ]

    lookup = api.build_variant_lookup()

    assert lookup == {"ABC-1": {"id": "1", "price": 100}}
    output = capsys.readouterr().out
    assert "[INFO] Loaded 1 variants into lookup" in output


def test_update_variant_validates_fields_and_rejects_empty_update():
    client = DummyClient(
        [{"data": {"updateProductVariant": {"id": "variant-1", "sku": "WL-2", "price": 1200, "enabled": True, "name": "Wall Lamp"}}}]
    )
    api = VariantsAPI(client)

    updated = api.update_variant(
        variant_id="variant-1",
        sku="WL-2",
        price=1200,
        enabled=True,
        name="Wall Lamp",
    )

    assert updated["sku"] == "WL-2"
    payload = client.calls[0]["variables"]["input"]
    assert payload["translations"][0]["name"] == "Wall Lamp"

    with pytest.raises(BeevoValidationError, match="requires at least one field to update"):
        api.update_variant("variant-1")


def test_update_variant_and_update_price_by_sku_handle_mismatches_and_missing_variants(capsys):
    client = DummyClient(
        [{"data": {"updateProductVariant": {"id": "variant-1", "sku": "WRONG", "price": 1000, "enabled": True, "name": "Wall Lamp"}}}]
    )
    api = VariantsAPI(client)

    with pytest.raises(BeevoValidationError, match="SKU not updated correctly"):
        api.update_variant(variant_id="variant-1", sku="WL-2")

    api.get_variant_by_sku = lambda sku: None
    api.update_price_by_sku("missing", 10.5)
    assert "[SKIP] SKU not found: missing" in capsys.readouterr().out

    calls = []
    api.get_variant_by_sku = lambda sku: {"id": "variant-2"}
    api.update_variant = lambda **kwargs: calls.append(kwargs)
    api.update_price_by_sku("WL-2", 10.5)
    output = capsys.readouterr().out
    assert calls == [{"variant_id": "variant-2", "price": 1050}]
    assert "[OK] WL-2" in output
