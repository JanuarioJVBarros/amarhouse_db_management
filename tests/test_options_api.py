import pytest

from beevo.exceptions import BeevoValidationError
from beevo.options import OptionsAPI


class DummyClient:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def request(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


def test_build_option_payload_supports_string_options():
    api = OptionsAPI(client=None)

    payload = api._build_option_payload("White", "pt_PT")

    assert payload == {
        "code": "white",
        "translations": [{"languageCode": "pt_PT", "name": "White"}],
    }


def test_build_option_payload_supports_dict_options():
    api = OptionsAPI(client=None)

    payload = api._build_option_payload({"code": "branco", "name": "Branco"}, "pt_PT")

    assert payload == {
        "code": "branco",
        "translations": [{"languageCode": "pt_PT", "name": "Branco"}],
    }


def test_build_option_payload_rejects_empty_name():
    api = OptionsAPI(client=None)

    with pytest.raises(BeevoValidationError, match="Option name cannot be empty"):
        api._build_option_payload({"code": "empty", "name": ""}, "pt_PT")


def test_create_option_group_sends_normalized_request_payload():
    client = DummyClient(
        {
            "data": {
                "createProductOptionGroup": {
                    "id": "group-1",
                    "name": "Color",
                    "options": [{"id": "opt-1", "name": "White"}],
                }
            }
        }
    )
    api = OptionsAPI(client)

    result = api.create_option_group(
        name="Color",
        options=["White"],
        code="color",
    )

    assert result["id"] == "group-1"
    request_call = client.calls[0]
    assert request_call["operation_name"] == "CreateProductOptionGroup"
    assert request_call["variables"]["input"]["code"] == "color"
    assert request_call["variables"]["input"]["options"][0]["code"] == "white"


def test_create_option_group_raises_for_name_mismatch():
    client = DummyClient(
        {
            "data": {
                "createProductOptionGroup": {
                    "id": "group-1",
                    "name": "Wrong Name",
                    "options": [],
                }
            }
        }
    )
    api = OptionsAPI(client)

    with pytest.raises(BeevoValidationError, match="Name mismatch"):
        api.create_option_group(name="Color", options=["White"])


def test_add_option_group_to_product_raises_for_product_id_mismatch():
    client = DummyClient(
        {
            "data": {
                "addOptionGroupToProduct": {
                    "id": "different-product",
                    "optionGroups": [{"id": "group-1"}],
                }
            }
        }
    )
    api = OptionsAPI(client)

    with pytest.raises(BeevoValidationError, match="Product ID mismatch"):
        api.add_option_group_to_product("prod-1", "group-1")
