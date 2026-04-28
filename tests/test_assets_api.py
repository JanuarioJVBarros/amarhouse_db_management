from pathlib import Path

import pytest
import requests

from beevo.assets import AssetsAPI
from beevo.exceptions import BeevoValidationError


class DummyClient:
    def __init__(self, response):
        self.response = response
        self.request_calls = []
        self.multipart_calls = []
        self.session = self
        self.timeout = 12

    def request(self, **kwargs):
        self.request_calls.append(kwargs)
        return self.response

    def request_multipart(self, files):
        self.multipart_calls.append(files)
        return self.response

    def get(self, *args, **kwargs):
        return requests.get(*args, **kwargs)


class DummyDownloadResponse:
    def __init__(self, chunks=None, content_type="image/png"):
        self.headers = {"Content-Type": content_type}
        self._chunks = chunks or [b"abc", b"123"]

    def raise_for_status(self):
        return None

    def iter_content(self, chunk_size=8192):
        return iter(self._chunks)


def test_upload_asset_downloads_and_returns_asset_id(monkeypatch, tmp_path):
    client = DummyClient({"data": {"createAssets": [{"id": "asset-1"}]}})
    api = AssetsAPI(client)
    removed_paths = []

    monkeypatch.setattr("beevo.assets.requests.get", lambda *args, **kwargs: DummyDownloadResponse())

    def fake_named_temporary_file(delete=False, suffix=""):
        path = tmp_path / f"upload{suffix}"
        handle = open(path, "w+b")
        return handle

    monkeypatch.setattr("beevo.assets.tempfile.NamedTemporaryFile", fake_named_temporary_file)
    monkeypatch.setattr("beevo.assets.os.unlink", lambda path: removed_paths.append(Path(path).name))

    asset_id = api.upload_asset("https://example.test/image.png")

    assert asset_id == "asset-1"
    assert client.multipart_calls, "Expected multipart upload to be used"
    assert removed_paths == ["upload.png"]


def test_upload_asset_uses_client_timeout_and_session(monkeypatch, tmp_path):
    client = DummyClient({"data": {"createAssets": [{"id": "asset-1"}]}})
    api = AssetsAPI(client)
    get_calls = []

    def fake_get(url, **kwargs):
        get_calls.append((url, kwargs))
        return DummyDownloadResponse()

    monkeypatch.setattr(client, "get", fake_get)

    def fake_named_temporary_file(delete=False, suffix=""):
        path = tmp_path / f"upload{suffix}"
        return open(path, "w+b")

    monkeypatch.setattr("beevo.assets.tempfile.NamedTemporaryFile", fake_named_temporary_file)
    monkeypatch.setattr("beevo.assets.os.unlink", lambda path: None)

    api.upload_asset("https://example.test/image.png")

    assert get_calls == [("https://example.test/image.png", {"stream": True, "timeout": 12})]


def test_upload_asset_raises_when_asset_id_is_missing(monkeypatch, tmp_path):
    client = DummyClient({"data": {"createAssets": [{}]}})
    api = AssetsAPI(client)

    monkeypatch.setattr("beevo.assets.requests.get", lambda *args, **kwargs: DummyDownloadResponse())

    def fake_named_temporary_file(delete=False, suffix=""):
        path = tmp_path / f"upload{suffix}"
        return open(path, "w+b")

    monkeypatch.setattr("beevo.assets.tempfile.NamedTemporaryFile", fake_named_temporary_file)
    monkeypatch.setattr("beevo.assets.os.unlink", lambda path: None)

    with pytest.raises(BeevoValidationError, match="Missing asset ID"):
        api.upload_asset("https://example.test/image.png")


def test_update_product_assets_validates_assets_field():
    client = DummyClient({"data": {"updateProduct": {"id": "prod-1", "assets": [{"id": "asset-1"}]}}})
    api = AssetsAPI(client)

    updated = api.update_product_assets("prod-1", ["asset-1"])

    assert updated["id"] == "prod-1"
    assert client.request_calls[0]["variables"]["input"]["assetIds"] == ["asset-1"]


def test_update_product_assets_raises_when_assets_are_missing():
    client = DummyClient({"data": {"updateProduct": {"id": "prod-1"}}})
    api = AssetsAPI(client)

    with pytest.raises(BeevoValidationError, match="Missing assets in response"):
        api.update_product_assets("prod-1", ["asset-1"])


def test_set_asset_as_featured_validates_featured_asset():
    client = DummyClient({"data": {"updateProduct": {"id": "prod-1", "featuredAsset": {"id": "asset-1"}}}})
    api = AssetsAPI(client)

    updated = api.set_asset_as_featured("prod-1", "asset-1")

    assert updated["featuredAsset"]["id"] == "asset-1"
    assert client.request_calls[0]["variables"]["input"]["featuredAssetId"] == "asset-1"


def test_set_asset_as_featured_raises_when_featured_asset_missing():
    client = DummyClient({"data": {"updateProduct": {"id": "prod-1", "featuredAsset": None}}})
    api = AssetsAPI(client)

    with pytest.raises(BeevoValidationError, match="Featured asset not set"):
        api.set_asset_as_featured("prod-1", "asset-1")
