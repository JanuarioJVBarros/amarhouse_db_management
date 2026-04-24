import pytest

from beevo.exceptions import BeevoValidationError
from beevo.validation import (
    require_fields,
    require_list,
    require_mapping,
    require_path,
    require_value,
)


def test_require_mapping_returns_mapping():
    payload = {"id": "123"}

    result = require_mapping(payload, "payload")

    assert result is payload


def test_require_mapping_raises_for_non_mapping():
    with pytest.raises(BeevoValidationError, match="payload must be a mapping/dict"):
        require_mapping(["not", "a", "mapping"], "payload")


def test_require_list_returns_list():
    items = [1, 2, 3]

    result = require_list(items, "items")

    assert result == items


def test_require_fields_raises_when_field_is_missing():
    with pytest.raises(BeevoValidationError, match="missing required field"):
        require_fields({"id": "1"}, ["id", "name"], "product")


def test_require_path_returns_nested_value():
    payload = {"data": {"product": {"id": "123"}}}

    result = require_path(payload, ["data", "product", "id"], "response")

    assert result == "123"


def test_require_path_raises_for_missing_nested_key():
    with pytest.raises(BeevoValidationError, match="missing required path: data.product.name"):
        require_path({"data": {"product": {}}}, ["data", "product", "name"], "response")


def test_require_value_raises_for_none():
    with pytest.raises(BeevoValidationError, match="price cannot be null"):
        require_value(None, "price")
