from config.headers import build_headers
import requests
import json

class BeevoClient:
    def __init__(self):
        self.base_url = Settings.BEEVO_URL

    def request(self, query, variables=None, operation_name=None):
        url = self.base_url

        headers = {
            "content-type": "application/json",
            "accept": "*/*",
            "origin": "https://amarhouse.beevo.com",
            "referer": "https://amarhouse.beevo.com/admin-api?languageCode=pt_PT",
            "apollo-require-preflight": "true",
            "user-agent": "Mozilla/5.0"
        }

        payload = {
            "query": query,
            "variables": variables or {},
            "operationName": operation_name,
        }

        response = requests.post(
            url,
            headers=headers,
            json=payload
        )

        # Debug output
        # print("\nURL:", url)
        # print("\nHEADERS:", headers)
        # print("\nPAYLOAD:", payload)

        try:
            response.raise_for_status()
        except Exception as e:
            print("\nHTTP ERROR:")
            print(response.text)
            raise e

        data = response.json()

        if "errors" in data:
            print("\nGRAPHQL ERROR:")
            print(json.dumps(data, indent=2, ensure_ascii=False))

        return data

    def request_multipart(self, files):

        headers = {
            "accept": "*/*",
            "origin": "https://amarhouse.beevo.com",
            "referer": "https://amarhouse.beevo.com/admin-api?languageCode=pt_PT",
            "apollo-require-preflight": "true",
            "user-agent": "Mozilla/5.0"
        }
                
        response = requests.post(
            self.base_url,
            headers=headers,
            files=files,
        )

        if not response.ok:
            raise Exception(f"Upload Error {response.status_code}: {response.text}")

        data = response.json()

        if "errors" in data:
            raise Exception(f"GraphQL Upload Error: {data['errors']}")

        return data
    

# DEBUG
if __name__ == "__main__":
    client = BeevoClient()

    query = """
            query {
            products {
                items {
                id
                name
                slug
                }
            }
            }
    """

    #variables={"id": "1"}

    response = client.request(query, variables={}, operation_name=None)

    print(response)


