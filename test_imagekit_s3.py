"""
Unit tests for imagekit_s3.py.

All boto3 / AWS calls are mocked via unittest.mock.  boto3 need not be
installed — the import inside S3ImageStore.client is intercepted before it
runs.  PIL is used for one fallback-download test; it is skipped if absent.
"""
import io
import os
import unittest.mock as mock
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest


# ── boto3 guard ───────────────────────────────────────────────────────────────

# We patch boto3 at the point where S3ImageStore imports it (inside the
# `client` property).  This means boto3 doesn't need to be installed.

def _make_store(bucket="test-bucket", region="us-east-1"):
    """Return an S3ImageStore with a mocked boto3 client."""
    from imagekit_s3 import S3ImageStore
    store = S3ImageStore(bucket=bucket, region=region)
    store._client = MagicMock()
    return store


# ── construction ──────────────────────────────────────────────────────────────

from imagekit_s3 import S3ImageStore


class TestS3ImageStoreInit:
    def test_bucket_and_region_stored(self):
        store = S3ImageStore(bucket="my-bucket", region="eu-west-1")
        assert store.bucket == "my-bucket"
        assert store.region == "eu-west-1"

    def test_base_url_constructed(self):
        store = S3ImageStore(bucket="my-bucket", region="eu-west-1")
        assert "my-bucket" in store.base_url
        assert "eu-west-1" in store.base_url

    def test_default_region_is_us_east_1(self):
        store = S3ImageStore(bucket="x")
        assert store.region == "us-east-1"

    def test_empty_bucket_raises(self):
        with pytest.raises(ValueError, match="bucket"):
            S3ImageStore(bucket="")


# ── url ───────────────────────────────────────────────────────────────────────

class TestS3ImageStoreUrl:
    def test_url_returns_base_url_plus_key(self):
        store = _make_store()
        url = store.url("0001.jpeg")
        assert url.startswith(store.base_url)
        assert "0001.jpeg" in url

    def test_url_encodes_spaces(self):
        store = _make_store()
        url = store.url("my photo.jpeg")
        assert " " not in url
        assert "%20" in url or "+" in url

    def test_url_preserves_thumbs_prefix(self):
        store = _make_store()
        url = store.url("thumbs/0001.jpeg")
        assert "thumbs/0001.jpeg" in url


# ── upload ────────────────────────────────────────────────────────────────────

class TestS3ImageStoreUpload:
    def test_upload_calls_upload_file(self, tmp_path):
        store = _make_store()
        local = tmp_path / "photo.jpg"
        local.write_bytes(b"fake jpeg")
        store.upload(local, "0001.jpeg")
        store._client.upload_file.assert_called_once()

    def test_upload_sets_content_type_jpeg(self, tmp_path):
        store = _make_store()
        local = tmp_path / "photo.jpeg"
        local.write_bytes(b"fake")
        store.upload(local, "0001.jpeg")
        _, kwargs = store._client.upload_file.call_args
        extra = kwargs.get("ExtraArgs", store._client.upload_file.call_args[0][3]
                           if len(store._client.upload_file.call_args[0]) > 3 else {})
        # Accept either positional or keyword ExtraArgs
        call_args = store._client.upload_file.call_args
        extra_args = call_args[1].get("ExtraArgs") or (
            call_args[0][3] if len(call_args[0]) > 3 else None
        )
        assert extra_args is not None
        assert extra_args.get("ContentType") == "image/jpeg"

    def test_upload_sets_content_type_png(self, tmp_path):
        store = _make_store()
        local = tmp_path / "photo.png"
        local.write_bytes(b"fake")
        store.upload(local, "image.png")
        call_args = store._client.upload_file.call_args
        extra_args = call_args[1].get("ExtraArgs") or (
            call_args[0][3] if len(call_args[0]) > 3 else None
        )
        assert extra_args["ContentType"] == "image/png"

    def test_upload_includes_dimension_metadata(self, tmp_path):
        store = _make_store()
        local = tmp_path / "photo.jpg"
        local.write_bytes(b"fake")
        store.upload(local, "0001.jpeg", width=1920, height=1080)
        call_args = store._client.upload_file.call_args
        extra_args = call_args[1].get("ExtraArgs") or call_args[0][3]
        assert extra_args["Metadata"]["width"] == "1920"
        assert extra_args["Metadata"]["height"] == "1080"

    def test_upload_no_metadata_when_dims_absent(self, tmp_path):
        store = _make_store()
        local = tmp_path / "photo.jpg"
        local.write_bytes(b"fake")
        store.upload(local, "0001.jpeg")
        call_args = store._client.upload_file.call_args
        extra_args = call_args[1].get("ExtraArgs") or call_args[0][3]
        assert "Metadata" not in extra_args

    def test_upload_passes_correct_bucket_and_key(self, tmp_path):
        store = _make_store(bucket="my-photos")
        local = tmp_path / "photo.jpg"
        local.write_bytes(b"fake")
        store.upload(local, "thumbs/0001.jpeg")
        call_args = store._client.upload_file.call_args
        # Positional: upload_file(local_path, bucket, key, ExtraArgs=...)
        args = call_args[0]
        assert args[1] == "my-photos"
        assert args[2] == "thumbs/0001.jpeg"


# ── list_images ───────────────────────────────────────────────────────────────

class TestS3ImageStoreListImages:
    def _make_page(self, keys):
        return {"Contents": [{"Key": k} for k in keys]}

    def test_returns_image_keys_excluding_thumbs(self):
        store = _make_store()
        paginator = MagicMock()
        paginator.paginate.return_value = [
            self._make_page(["0001.jpeg", "0002.jpeg", "thumbs/0001.jpeg"])
        ]
        store._client.get_paginator.return_value = paginator
        keys = store.list_images()
        assert "0001.jpeg" in keys
        assert "0002.jpeg" in keys
        assert "thumbs/0001.jpeg" not in keys

    def test_returns_empty_for_empty_bucket(self):
        store = _make_store()
        paginator = MagicMock()
        paginator.paginate.return_value = [{"Contents": []}]
        store._client.get_paginator.return_value = paginator
        assert store.list_images() == []

    def test_handles_missing_contents_key(self):
        store = _make_store()
        paginator = MagicMock()
        paginator.paginate.return_value = [{}]
        store._client.get_paginator.return_value = paginator
        assert store.list_images() == []

    def test_filters_by_extension(self):
        store = _make_store()
        paginator = MagicMock()
        paginator.paginate.return_value = [
            self._make_page(["0001.jpeg", "0002.png", "0003.gif"])
        ]
        store._client.get_paginator.return_value = paginator
        keys = store.list_images(extensions=(".jpeg",))
        assert keys == ["0001.jpeg"]

    def test_paginates_multiple_pages(self):
        store = _make_store()
        paginator = MagicMock()
        paginator.paginate.return_value = [
            self._make_page(["0001.jpeg"]),
            self._make_page(["0002.jpeg"]),
        ]
        store._client.get_paginator.return_value = paginator
        keys = store.list_images()
        assert len(keys) == 2


# ── find_next_number ──────────────────────────────────────────────────────────

class TestS3ImageStoreFindNextNumber:
    def _make_page(self, keys):
        return {"Contents": [{"Key": k} for k in keys]}

    def test_returns_1_for_empty_bucket(self):
        store = _make_store()
        paginator = MagicMock()
        paginator.paginate.return_value = [{}]
        store._client.get_paginator.return_value = paginator
        assert store.find_next_number() == 1

    def test_returns_max_plus_one(self):
        store = _make_store()
        paginator = MagicMock()
        paginator.paginate.return_value = [
            self._make_page(["0001.jpeg", "0042.jpeg", "0007.jpeg"])
        ]
        store._client.get_paginator.return_value = paginator
        assert store.find_next_number() == 43

    def test_skips_thumbs(self):
        store = _make_store()
        paginator = MagicMock()
        paginator.paginate.return_value = [
            self._make_page(["0001.jpeg", "thumbs/9999.jpeg"])
        ]
        store._client.get_paginator.return_value = paginator
        assert store.find_next_number() == 2

    def test_skips_non_numeric_keys(self):
        store = _make_store()
        paginator = MagicMock()
        paginator.paginate.return_value = [
            self._make_page(["banner.jpeg", "0003.jpeg"])
        ]
        store._client.get_paginator.return_value = paginator
        assert store.find_next_number() == 4


# ── get_dimensions ────────────────────────────────────────────────────────────

class TestS3ImageStoreGetDimensions:
    def test_reads_dimensions_from_metadata(self):
        store = _make_store()
        store._client.head_object.return_value = {
            "Metadata": {"width": "1920", "height": "1080"}
        }
        w, h = store.get_dimensions("0001.jpeg")
        assert w == 1920
        assert h == 1080

    def test_falls_back_to_download_when_metadata_missing(self):
        """When metadata lacks dimensions, the image body is downloaded."""
        PIL = pytest.importorskip("PIL", reason="Pillow not installed")
        from PIL import Image

        store = _make_store()
        store._client.head_object.return_value = {"Metadata": {}}

        img = Image.new("RGB", (640, 480))
        buf = io.BytesIO()
        img.save(buf, "JPEG")
        buf.seek(0)

        mock_response = {"Body": buf}
        store._client.get_object.return_value = mock_response

        w, h = store.get_dimensions("0001.jpeg")
        assert w == 640
        assert h == 480

    def test_falls_back_when_metadata_has_zeros(self):
        """Dimensions of 0x0 in metadata trigger the download fallback."""
        PIL = pytest.importorskip("PIL", reason="Pillow not installed")
        from PIL import Image

        store = _make_store()
        store._client.head_object.return_value = {
            "Metadata": {"width": "0", "height": "0"}
        }

        img = Image.new("RGB", (300, 200))
        buf = io.BytesIO()
        img.save(buf, "JPEG")
        buf.seek(0)

        store._client.get_object.return_value = {"Body": buf}

        w, h = store.get_dimensions("0001.jpeg")
        assert w == 300
        assert h == 200

    def test_handles_corrupt_metadata_values(self):
        """Non-integer metadata triggers the download fallback."""
        PIL = pytest.importorskip("PIL", reason="Pillow not installed")
        from PIL import Image

        store = _make_store()
        store._client.head_object.return_value = {
            "Metadata": {"width": "n/a", "height": "n/a"}
        }

        img = Image.new("RGB", (100, 50))
        buf = io.BytesIO()
        img.save(buf, "JPEG")
        buf.seek(0)

        store._client.get_object.return_value = {"Body": buf}

        w, h = store.get_dimensions("0001.jpeg")
        assert w == 100
        assert h == 50


# ── count_objects ─────────────────────────────────────────────────────────────

class TestS3ImageStoreCountObjects:
    def test_counts_all_objects(self):
        store = _make_store()
        paginator = MagicMock()
        paginator.paginate.return_value = [
            {"Contents": [{"Key": "a"}, {"Key": "b"}]},
            {"Contents": [{"Key": "c"}]},
        ]
        store._client.get_paginator.return_value = paginator
        assert store.count_objects() == 3

    def test_returns_zero_for_empty_bucket(self):
        store = _make_store()
        paginator = MagicMock()
        paginator.paginate.return_value = [{}]
        store._client.get_paginator.return_value = paginator
        assert store.count_objects() == 0


# ── delete_all ────────────────────────────────────────────────────────────────

class TestS3ImageStoreDeleteAll:
    def _setup_delete(self, store, keys):
        """Wire up paginator to return keys and delete_objects to succeed."""
        paginator = MagicMock()
        paginator.paginate.return_value = [
            {"Contents": [{"Key": k} for k in keys]}
        ]
        store._client.get_paginator.return_value = paginator
        store._client.delete_objects.return_value = {
            "Deleted": [{"Key": k} for k in keys],
            "Errors": [],
        }

    def test_deletes_all_objects_without_confirm(self):
        store = _make_store()
        self._setup_delete(store, ["0001.jpeg", "0002.jpeg"])
        deleted = store.delete_all(confirm=False)
        assert deleted == 2
        store._client.delete_objects.assert_called_once()

    def test_returns_zero_for_empty_bucket(self):
        store = _make_store()
        paginator = MagicMock()
        paginator.paginate.return_value = [{}]
        store._client.get_paginator.return_value = paginator
        deleted = store.delete_all(confirm=False)
        assert deleted == 0

    def test_reports_partial_errors(self, capsys):
        store = _make_store()
        keys = ["0001.jpeg", "0002.jpeg"]
        paginator = MagicMock()
        paginator.paginate.return_value = [
            {"Contents": [{"Key": k} for k in keys]}
        ]
        store._client.get_paginator.return_value = paginator
        store._client.delete_objects.return_value = {
            "Deleted": [{"Key": "0001.jpeg"}],
            "Errors": [{"Key": "0002.jpeg", "Message": "Access Denied"}],
        }
        deleted = store.delete_all(confirm=False)
        assert deleted == 1
        out = capsys.readouterr().out
        assert "0002.jpeg" in out

    def test_confirm_true_aborts_on_wrong_phrase(self, monkeypatch):
        store = _make_store()
        paginator = MagicMock()
        paginator.paginate.return_value = [
            {"Contents": [{"Key": "0001.jpeg"}]}
        ]
        store._client.get_paginator.return_value = paginator
        monkeypatch.setattr("builtins.input", lambda _: "wrong answer")
        deleted = store.delete_all(confirm=True)
        assert deleted == 0
        store._client.delete_objects.assert_not_called()

    def test_confirm_true_proceeds_on_correct_phrase(self, monkeypatch):
        store = _make_store()
        keys = ["0001.jpeg"]
        paginator = MagicMock()
        paginator.paginate.return_value = [
            {"Contents": [{"Key": k} for k in keys]}
        ]
        store._client.get_paginator.return_value = paginator
        store._client.delete_objects.return_value = {
            "Deleted": [{"Key": k} for k in keys],
            "Errors": [],
        }
        # Correct phrase is "delete 1 objects"
        monkeypatch.setattr("builtins.input", lambda _: "delete 1 objects")
        deleted = store.delete_all(confirm=True)
        assert deleted == 1
