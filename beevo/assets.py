import os
import json
import requests
import tempfile

from beevo.exceptions import BeevoValidationError
from beevo.validation import require_list, require_mapping, require_path


class AssetsAPI:
    def __init__(self, client):
        self.client = client

    def upload_asset(self, image_url, expected_status=200):
        """
        Downloads an image from a URL and uploads it as an asset.
        Returns asset ID.
        """
        if not image_url:
            raise BeevoValidationError("Image URL is required for asset upload")

        session = getattr(self.client, "session", requests)
        timeout = getattr(self.client, "timeout", None)
        request_kwargs = {"stream": True}
        if timeout is not None:
            request_kwargs["timeout"] = timeout

        # Reusing the Beevo client session keeps transport policy consistent
        # across the repo and avoids introducing a second set of network
        # defaults just for asset downloads.
        resp = session.get(image_url, **request_kwargs)
        file_path = None

        try:
            resp.raise_for_status()

            content_type = resp.headers.get("Content-Type", "image/jpeg")
            extension = content_type.split("/")[-1].split(";")[0]

            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{extension}") as tmp_file:
                file_path = tmp_file.name
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        # Iterating in chunks prevents large supplier images
                        # from being buffered fully into memory.
                        tmp_file.write(chunk)

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
            assets = require_list(
                require_path(response, ["data", "createAssets"], "upload_asset response"),
                "upload_asset response.data.createAssets",
            )

            if not assets:
                raise BeevoValidationError("Asset upload returned an empty list")

            asset = require_mapping(assets[0], "upload_asset first asset")

            if not asset.get("id"):
                raise BeevoValidationError(f"Missing asset ID: {asset}")

            return asset["id"]

        finally:
            # We always try to release the network response and delete the
            # temporary file, even when Beevo rejects the multipart upload.
            try:
                if hasattr(resp, "close"):
                    resp.close()
            except Exception:
                pass
            try:
                if file_path:
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

        updated = require_mapping(
            require_path(response, ["data", "updateProduct"], "update_product_assets response"),
            "update_product_assets response.data.updateProduct",
        )

        if "assets" not in updated:
            raise BeevoValidationError("Missing assets in response")

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

        updated = require_mapping(
            require_path(response, ["data", "updateProduct"], "set_asset_as_featured response"),
            "set_asset_as_featured response.data.updateProduct",
        )

        if not updated.get("featuredAsset"):
            raise BeevoValidationError("Featured asset not set")

        return updated
