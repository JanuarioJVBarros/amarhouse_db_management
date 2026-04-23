from beevo.config.config import BEEVO_URL, BEEVO_COOKIE
import requests
import json

class BeevoClient:
    def __init__(self, base_url=BEEVO_URL, beevo_cookie=BEEVO_COOKIE):
        self.base_url = base_url
        self.beevo_cookie = beevo_cookie

    def request(self, query, variables=None, operation_name=None, expected_status=200):
        payload = {
            "query": query,
            "variables": variables or {},
            "operationName": operation_name,
        }

        headers = {
            "content-type": "application/json",
            "accept": "*/*",
            "origin": "https://amarhouse.beevo.com",
            "referer": "https://amarhouse.beevo.com/admin-api?languageCode=pt_PT",
            "cookie": self.beevo_cookie,
            "apollo-require-preflight": "true",
            "user-agent": "Mozilla/5.0"
        }

        response = requests.post(
            self.base_url,
            headers=headers,
            json=payload
        )

        # -------------------------
        # STATUS CODE VALIDATION
        # -------------------------
        assert response.status_code == expected_status, (
            f"Unexpected status code: "
            f"{response.status_code} (expected {expected_status})\n"
            f"Response: {response.text}"
        )

        # -------------------------
        # PARSE RESPONSE
        # -------------------------
        try:
            data = response.json()
        except Exception:
            raise AssertionError(f"Response is not valid JSON:\n{response.text}")

        # -------------------------
        # GRAPHQL ERROR CHECK
        # -------------------------
        if "errors" in data:
            raise AssertionError(
                "GraphQL errors detected:\n"
                f"{json.dumps(data['errors'], indent=2)}"
            )

        return data

    # -------------------------
    # MULTIPART REQUEST
    # -------------------------
    def request_multipart(self, files, expected_status=200):

        headers = {
            "accept": "*/*",
            "origin": "https://amarhouse.beevo.com",
            "referer": "https://amarhouse.beevo.com/admin-api?languageCode=pt_PT",
            "apollo-require-preflight": "true",
            "user-agent": "Mozilla/5.0",
            "cookie": self.beevo_cookie
        }

        response = requests.post(
            self.base_url,
            headers=headers,
            files=files,
        )

        # STATUS VALIDATION
        assert response.status_code == expected_status, (
            f"Unexpected upload status: {response.status_code}"
        )

        try:
            data = response.json()
        except Exception:
            raise AssertionError(f"Upload response is not JSON:\n{response.text}")

        if "errors" in data:
            raise AssertionError(
                f"GraphQL upload errors:\n{json.dumps(data['errors'], indent=2)}"
            )

        return data