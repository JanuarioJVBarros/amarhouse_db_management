import os
import json
import requests
import tempfile

class AssetsAPI:
    def __init__(self, client):
        self.client = client

    def upload_asset(self, image_url):
        """
        Downloads an image from a URL and uploads it to Beevo as an asset.
        Returns the asset ID.
        """

        # 1. Download image from URL
        resp = requests.get(image_url, stream=True)
        resp.raise_for_status()

        content_type = resp.headers.get("Content-Type", "image/jpeg")
        extension = content_type.split("/")[-1].split(";")[0]

        tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f".{extension}")

        file_path = tmp_file.name

        try:
            for chunk in resp.iter_content(chunk_size=8192):
                tmp_file.write(chunk)

            tmp_file.close()

            query = """
                    mutation CreateAssets($input: [CreateAssetInput!]!) {
                    createAssets(input: $input) {
                        ... on Asset {
                        id
                        name
                        fileSize
                        mimeType
                        preview
                        source
                        }

                        ... on ErrorResult {
                        message
                        }
                    }
                    }
            """

            operations = {
                "operationName": "CreateAssets",
                "query": query,
                "variables": {
                    "input": [
                        {"file": None}
                    ]
                }
            }

            map_data = {
                "1": ["variables.input.0.file"]
            }

            # 3. Upload via multipart (IMPORTANT: file handle)
            with open(file_path, "rb") as file_handle:
                files = {
                    "operations": (None, json.dumps(operations), "application/json"),
                    "map": (None, json.dumps(map_data), "application/json"),
                    "1": (os.path.basename(file_path), file_handle, content_type)
                }

                response = self.client.request_multipart(files)

            asset = response["data"]["createAssets"][0]

            if asset.get("id"):
                return asset["id"]

            raise Exception(f"Upload failed: {asset}")

        finally:
            # 4. cleanup temp file
            try:
                os.unlink(file_path)
            except Exception:
                pass

    def update_product_assets(self, product_id, asset_ids):
        """
        Attaches uploaded assets to a product
        """

        query = """
            mutation UpdateProduct($input: UpdateProductInput!) {
            updateProduct(input: $input) {
                id
                name
                slug
                assets {
                id
                preview
                }
                featuredAsset {
                id
                preview
                }
            }
            }
        """

        variables = {
            "input": {
                "id": product_id,
                "assetIds": asset_ids
            }
        }

        return self.client.request(
            query=query,
            variables=variables,
            operation_name="UpdateProduct"
        )
    
    def set_asset_as_featured(self, product_id, asset_id):
        query = """
            mutation UpdateProduct($input: UpdateProductInput!) {
            updateProduct(input: $input) {
                id
                name
                featuredAsset {
                id
                preview
                }
                assets {
                id
                preview
                }
            }
            }
        """

        variables = {
            "input": {
                "id": product_id,
                "featuredAssetId": asset_id
            }
        }
        
        
        return self.client.request(
            query=query,
            variables=variables,
            operation_name="UpdateProduct"
        )
