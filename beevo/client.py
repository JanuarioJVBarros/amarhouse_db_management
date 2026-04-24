import json
import requests

from beevo.config.config import get_settings
from beevo.exceptions import (
    BeevoConfigurationError,
    BeevoResponseError,
    BeevoTransportError,
)

class BeevoClient:
    def __init__(
        self,
        base_url=None,
        beevo_cookie=None,
        timeout=None,
        session=None,
    ):
        settings = None

        if base_url is None or beevo_cookie is None or timeout is None:
            settings = get_settings(validate=False)

        self.base_url = base_url if base_url is not None else settings.beevo_url
        self.beevo_cookie = beevo_cookie if beevo_cookie is not None else settings.beevo_cookie
        self.timeout = timeout if timeout is not None else settings.request_timeout
        self.session = session or requests.Session()

        if not self.base_url:
            raise BeevoConfigurationError("Beevo base URL is required")

        if not self.beevo_cookie:
            raise BeevoConfigurationError("Beevo cookie is required")

        if self.timeout <= 0:
            raise BeevoConfigurationError("Request timeout must be greater than zero")

    def _build_headers(self):
        return {
            "content-type": "application/json",
            "accept": "*/*",
            "origin": "https://amarhouse.beevo.com",
            "referer": "https://amarhouse.beevo.com/admin-api?languageCode=pt_PT",
            "cookie": self.beevo_cookie,
            "apollo-require-preflight": "true",
            "user-agent": "Mozilla/5.0"
        }

    def _validate_response(self, response, expected_status, context):
        if response.status_code != expected_status:
            raise BeevoResponseError(
                f"{context} returned unexpected status code: "
                f"{response.status_code} (expected {expected_status})\n"
                f"Response: {response.text}"
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise BeevoResponseError(f"{context} response is not valid JSON:\n{response.text}") from exc

        if "errors" in data:
            raise BeevoResponseError(
                f"{context} GraphQL errors detected:\n"
                f"{json.dumps(data['errors'], indent=2)}"
            )

        return data

    def request(self, query, variables=None, operation_name=None, expected_status=200):
        payload = {
            "query": query,
            "variables": variables or {},
            "operationName": operation_name,
        }

        try:
            response = self.session.post(
                self.base_url,
                headers=self._build_headers(),
                json=payload,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise BeevoTransportError(f"Beevo request failed: {exc}") from exc

        return self._validate_response(
            response=response,
            expected_status=expected_status,
            context=operation_name or "Beevo request",
        )

    # -------------------------
    # MULTIPART REQUEST
    # -------------------------
    def request_multipart(self, files, expected_status=200):
        try:
            response = self.session.post(
                self.base_url,
                headers={key: value for key, value in self._build_headers().items() if key != "content-type"},
                files=files,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise BeevoTransportError(f"Beevo multipart request failed: {exc}") from exc

        return self._validate_response(
            response=response,
            expected_status=expected_status,
            context="Beevo multipart request",
        )
