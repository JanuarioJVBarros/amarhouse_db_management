import pytest

from beevo.facets import FacetsAPI
from beevo.labels import LabelsAPI
from beevo.exceptions import BeevoValidationError


class DummyClient:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def request(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


def test_get_facet_values_returns_items_and_uses_id_filter():
    client = DummyClient({"data": {"facetValues": {"items": [{"id": "1", "name": "Indoor", "code": "indoor"}]}}})
    api = LabelsAPI(client)

    items = api.get_facet_values(["1", "2"])

    assert items == [{"id": "1", "name": "Indoor", "code": "indoor"}]
    assert client.calls[0]["variables"]["options"]["filter"]["id"]["in"] == ["1", "2"]


def test_get_facet_values_raises_for_invalid_shape():
    client = DummyClient({"data": {"facetValues": {"items": None}}})
    api = LabelsAPI(client)

    with pytest.raises(BeevoValidationError, match="must be a list"):
        api.get_facet_values(["1"])


def test_add_labels_to_product_returns_update_product_and_sends_ids():
    client = DummyClient({"data": {"updateProduct": {"id": "prod-1"}}})
    api = LabelsAPI(client)

    updated = api.add_labels_to_product("prod-1", ["127", "128"])

    assert updated == {"id": "prod-1"}
    assert client.calls[0]["variables"]["input"]["facetValueIds"] == ["127", "128"]


def test_get_facets_returns_items():
    client = DummyClient({"data": {"facets": {"items": [{"id": "f1", "name": "Category", "values": []}]}}})
    api = FacetsAPI(client)

    items = api.get_facets()

    assert items == [{"id": "f1", "name": "Category", "values": []}]
    assert client.calls[0]["operation_name"] == "GetFacets"


def test_get_products_by_facet_value_returns_search_items():
    client = DummyClient({"data": {"search": {"items": [{"productName": "Wall Lamp", "sku": "WL-1"}]}}})
    api = FacetsAPI(client)

    items = api.get_products_by_facet_value("127")

    assert items == [{"productName": "Wall Lamp", "sku": "WL-1"}]
    variables = client.calls[0]["variables"]["input"]
    assert variables["facetValueIds"] == ["127"]
    assert variables["groupByProduct"] is False


def test_get_products_by_facet_value_raises_for_invalid_shape():
    client = DummyClient({"data": {"search": {"items": "not-a-list"}}})
    api = FacetsAPI(client)

    with pytest.raises(BeevoValidationError, match="must be a list"):
        api.get_products_by_facet_value("127")
