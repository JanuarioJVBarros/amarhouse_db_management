from config.settings import Settings
from config.headers import build_headers
import requests


class BeevoClient:
    def __init__(self, url=None, token=None, cookie=None, language=None):
        self.url = url or Settings.BEEVO_URL
        self.language = language or Settings.LANGUAGE_CODE

        self.headers = build_headers(
            token=token or Settings.BEEVO_TOKEN,
            cookie=cookie or Settings.BEEVO_COOKIE
        )

    def request(self, query, variables=None, operation_name=None):
        payload = {
            "query": query,
            "variables": variables or {},
        }

        if operation_name:
            payload["operationName"] = operation_name

        response = requests.post(self.url, json=payload, headers=self.headers)

        if not response.ok:
            raise Exception(f"HTTP Error {response.status_code}: {response.text}")

        data = response.json()

        if "errors" in data:
            raise Exception(f"GraphQL Error: {data['errors']}")

        return data["data"]

    def request_multipart(self, files):
        response = requests.post(
            self.url,
            files=files,
            headers={
                "beeevo-token": self.headers.get("beeevo-token"),
                "cookie": self.headers.get("cookie"),
            }
        )

        if not response.ok:
            raise Exception(f"Upload Error {response.status_code}: {response.text}")

        data = response.json()

        if "errors" in data:
            raise Exception(f"GraphQL Upload Error: {data['errors']}")

        return data