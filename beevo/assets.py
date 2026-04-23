import os
import json
import requests
import tempfile


class AssetsAPI:
    def __init__(self, client):
        self.client = client


    def upload_asset(self, image_url, expected_status=200):
        """
        Downloads an image from a URL and uploads it as an asset.
        Returns asset ID.
        """

        # -------------------------
        # DOWNLOAD IMAGE
        # -------------------------
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

            # -------------------------
            # MULTIPART UPLOAD
            # -------------------------
            with open(file_path, "rb") as file_handle:
                files = {
                    "operations": (None, json.dumps(operations), "application/json"),
                    "map": (None, json.dumps(map_data), "application/json"),
                    "1": (os.path.basename(file_path), file_handle, content_type)
                }

                response = self.client.request_multipart(files)

            # -------------------------
            # VALIDATION
            # -------------------------
            assets = response.get("data", {}).get("createAssets", [])

            assert assets, f"Asset upload failed: {response}"

            asset = assets[0]

            assert asset.get("id"), f"Missing asset ID: {asset}"

            return asset["id"]

        finally:
            # -------------------------
            # CLEANUP
            # -------------------------
            try:
                os.unlink(file_path)
            except Exception:
                pass


    def update_product_assets(self, product_id, asset_ids, expected_status=200):
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

        response = self.client.request(
            query=query,
            variables=variables,
            operation_name="UpdateProduct",
            expected_status=expected_status
        )

        updated = response.get("data", {}).get("updateProduct")

        assert updated is not None, f"Asset update failed: {response}"
        assert "assets" in updated, "Missing assets in response"

        return updated

 
    def set_asset_as_featured(self, product_id, asset_id, expected_status=200):
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

        response = self.client.request(
            query=query,
            variables=variables,
            operation_name="UpdateProduct",
            expected_status=expected_status
        )

        updated = response.get("data", {}).get("updateProduct")

        assert updated is not None, f"Setting featured asset failed: {response}"
        assert updated.get("featuredAsset"), "Featured asset not set"

        return updated