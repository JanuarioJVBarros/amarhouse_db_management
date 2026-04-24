import pytest
import requests

from beevo.client import BeevoClient
from beevo.exceptions import BeevoResponseError, BeevoTransportError


class DummyResponse:
    def __init__(self, status_code=200, payload=None, text="{}", json_error=None):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.text = text
        self._json_error = json_error

    def json(self):
        if self._json_error is not None:
            raise self._json_error
        return self._payload


class DummySession:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.calls = []

    def post(self, url, headers=None, json=None, files=None, timeout=None):
        self.calls.append(
            {
                "url": url,
                "headers": headers,
                "json": json,
                "files": files,
                "timeout": timeout,
            }
        )
        if self.error is not None:
            raise self.error
        return self.response


def test_request_returns_parsed_payload_and_uses_timeout():
    session = DummySession(
        response=DummyResponse(payload={"data": {"healthcheck": True}})
    )
    client = BeevoClient(
        base_url="https://example.test/graphql",
        beevo_cookie="session=abc",
        timeout=15,
        session=session,
    )

    payload = client.request("query { healthcheck }", operation_name="Healthcheck")

    assert payload == {"data": {"healthcheck": True}}
    assert session.calls[0]["timeout"] == 15
    assert session.calls[0]["headers"]["cookie"] == "session=abc"


def test_request_raises_for_unexpected_status():
    session = DummySession(
        response=DummyResponse(status_code=500, payload={"message": "nope"}, text="server error")
    )
    client = BeevoClient(
        base_url="https://example.test/graphql",
        beevo_cookie="session=abc",
        session=session,
    )

    with pytest.raises(BeevoResponseError, match="unexpected status code"):
        client.request("query { test }", operation_name="StatusCheck")


def test_request_raises_for_graphql_errors():
    session = DummySession(
        response=DummyResponse(payload={"errors": [{"message": "boom"}]})
    )
    client = BeevoClient(
        base_url="https://example.test/graphql",
        beevo_cookie="session=abc",
        session=session,
    )

    with pytest.raises(BeevoResponseError, match="GraphQL errors detected"):
        client.request("query { test }", operation_name="GraphQLCheck")


def test_request_wraps_transport_failures():
    session = DummySession(error=requests.RequestException("socket closed"))
    client = BeevoClient(
        base_url="https://example.test/graphql",
        beevo_cookie="session=abc",
        session=session,
    )

    with pytest.raises(BeevoTransportError, match="Beevo request failed"):
        client.request("query { test }", operation_name="TransportCheck")
