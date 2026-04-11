import requests


class AssetsAPI:
    def __init__(self, client):
        self.client = client

    def upload_asset(self, file_path):
        """
        Uploads an image and returns asset ID
        using Apollo GraphQL multipart upload
        """

        query = """
        mutation CreateAssets($input: [CreateAssetInput!]!) {
          createAssets(input: $input) {
            ... on Asset {
              id
              name
              preview
            }
            ... on ErrorResult {
              message
            }
          }
        }
        """

        operations = {
            "operationName": "CreateAssets",
            "variables": {
                "input": [
                    {"file": None}
                ]
            },
            "query": query
        }

        map_data = {
            "1": ["variables.input.0.file"]
        }

        with open(file_path, "rb") as f:
            files = {
                "operations": (None, str(operations), "application/json"),
                "map": (None, str(map_data), "application/json"),
                "1": (file_path.split("/")[-1], f, "image/jpeg")
            }

            response = self.client.request_multipart(files)

        # extract result
        data = response["data"]["createAssets"][0]

        if isinstance(data, dict) and data.get("id"):
            return data["id"]

        raise Exception(f"Upload failed: {data}")