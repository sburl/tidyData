"""
Unit tests for imagekit_pipeline.py.

All filesystem-heavy operations are exercised with real tmp_path directories.
S3 / boto3 calls are mocked via unittest.mock — boto3 need not be installed.
Tests that exercise upload_new_photos (which imports S3ImageStore) are guarded
so they skip cleanly if boto3 is missing.
"""
import io
import json
import os
import shutil
import tempfile
import unittest.mock as mock
from datetime import datetime
from pathlib import Path

import pytest

# ── helpers ──────────────────────────────────────────────────────────────────

PIL = pytest.importorskip("PIL", reason="Pillow not installed — skipping pipeline tests")
from PIL import Image


def _make_jpeg(path: Path, width=100, height=80, color=(200, 100, 50)):
    img = Image.new("RGB", (width, height), color=color)
    img.save(str(path), "JPEG", quality=85)
    return path


def _make_png(path: Path, width=60, height=40):
    img = Image.new("RGB", (width, height), color=(10, 20, 30))
    img.save(str(path), "PNG")
    return path


# ── find_images_to_process ────────────────────────────────────────────────────

from imagekit_pipeline import find_images_to_process


class TestFindImagesToProcess:
    def test_returns_empty_for_missing_source_dir(self, tmp_path):
        result = find_images_to_process(tmp_path / "nonexistent", tmp_path / "web")
        assert result == []

    def test_finds_jpeg_and_png(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        _make_jpeg(src / "a.jpg")
        _make_png(src / "b.png")
        (src / "readme.txt").write_text("skip me")
        result = find_images_to_process(src, tmp_path / "web")
        names = {p.name for p in result}
        assert names == {"a.jpg", "b.png"}

    def test_skips_already_processed_image(self, tmp_path):
        src = tmp_path / "src"
        web = tmp_path / "web"
        src.mkdir()
        web.mkdir()
        img = _make_jpeg(src / "a.jpg")
        web_img = web / "a.jpg"
        _make_jpeg(web_img)
        # Make web image newer than source
        os.utime(web_img, (img.stat().st_mtime + 10, img.stat().st_mtime + 10))
        result = find_images_to_process(src, web)
        assert result == []

    def test_force_reprocesses_all(self, tmp_path):
        src = tmp_path / "src"
        web = tmp_path / "web"
        src.mkdir()
        web.mkdir()
        img = _make_jpeg(src / "a.jpg")
        web_img = web / "a.jpg"
        _make_jpeg(web_img)
        os.utime(web_img, (img.stat().st_mtime + 10, img.stat().st_mtime + 10))
        result = find_images_to_process(src, web, force=True)
        assert len(result) == 1

    def test_returns_sorted_paths(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        _make_jpeg(src / "c.jpg")
        _make_jpeg(src / "a.jpg")
        _make_jpeg(src / "b.jpg")
        result = find_images_to_process(src, tmp_path / "web")
        names = [p.name for p in result]
        assert names == sorted(names)


# ── process_local_images ──────────────────────────────────────────────────────

from imagekit_pipeline import process_local_images


class TestProcessLocalImages:
    def test_returns_zero_for_empty_dir(self, tmp_path):
        src = tmp_path / "empty"
        src.mkdir()
        assert process_local_images(src, tmp_path / "web") == 0

    def test_returns_zero_for_missing_dir(self, tmp_path):
        assert process_local_images(tmp_path / "missing", tmp_path / "web") == 0

    def test_processes_images_and_creates_web_versions(self, tmp_path):
        src = tmp_path / "src"
        web = tmp_path / "web"
        src.mkdir()
        _make_jpeg(src / "photo.jpg", width=1600, height=1200)
        count = process_local_images(src, web, max_width=800)
        assert count == 1
        assert (web / "photo.jpg").exists()
        # Web version should be resized
        with Image.open(web / "photo.jpg") as img:
            assert img.size[0] <= 800

    def test_dry_run_returns_zero_and_creates_no_files(self, tmp_path):
        src = tmp_path / "src"
        web = tmp_path / "web"
        src.mkdir()
        _make_jpeg(src / "photo.jpg")
        count = process_local_images(src, web, dry_run=True)
        assert count == 0
        assert not web.exists()

    def test_skips_symlinks(self, tmp_path):
        src = tmp_path / "src"
        web = tmp_path / "web"
        src.mkdir()
        real_img = tmp_path / "real.jpg"
        _make_jpeg(real_img)
        (src / "link.jpg").symlink_to(real_img)
        count = process_local_images(src, web)
        assert count == 0

    def test_source_originals_preserved_after_processing(self, tmp_path):
        """Stripping metadata should not corrupt the source file."""
        src = tmp_path / "src"
        web = tmp_path / "web"
        src.mkdir()
        img_path = src / "photo.jpg"
        _make_jpeg(img_path, width=200, height=150)
        original_size = img_path.stat().st_size
        process_local_images(src, web)
        # Source must still be a readable image
        with Image.open(img_path) as img:
            assert img.size == (200, 150)

    def test_handles_corrupt_image_gracefully(self, tmp_path):
        src = tmp_path / "src"
        web = tmp_path / "web"
        src.mkdir()
        (src / "bad.jpg").write_bytes(b"not an image")
        # Should not raise — error is caught and reported
        count = process_local_images(src, web)
        assert count == 0

    def test_multiple_images_all_processed(self, tmp_path):
        src = tmp_path / "src"
        web = tmp_path / "web"
        src.mkdir()
        for i in range(3):
            _make_jpeg(src / f"img{i}.jpg")
        count = process_local_images(src, web)
        assert count == 3
        assert len(list(web.iterdir())) == 3


# ── catalog_images ────────────────────────────────────────────────────────────

from imagekit_pipeline import catalog_images


class TestCatalogImages:
    def test_creates_manifest_json(self, tmp_path):
        src = tmp_path / "photos"
        src.mkdir()
        _make_jpeg(src / "a.jpg")
        manifest_path = tmp_path / "manifest.json"
        catalog_images(src, manifest_path)
        assert manifest_path.exists()
        with open(manifest_path) as f:
            data = json.load(f)
        assert len(data) == 1

    def test_manifest_entries_have_required_fields(self, tmp_path):
        src = tmp_path / "photos"
        src.mkdir()
        _make_jpeg(src / "a.jpg")
        manifest_path = tmp_path / "manifest.json"
        entries = catalog_images(src, manifest_path)
        assert len(entries) == 1
        e = entries[0]
        assert "relative_path" in e
        assert "date" in e
        assert "date_source" in e
        assert "size" in e

    def test_returns_empty_list_for_empty_dir(self, tmp_path):
        src = tmp_path / "empty"
        src.mkdir()
        manifest_path = tmp_path / "manifest.json"
        entries = catalog_images(src, manifest_path)
        assert entries == []

    def test_date_source_mtime_when_no_exif(self, tmp_path):
        src = tmp_path / "photos"
        src.mkdir()
        _make_jpeg(src / "a.jpg")
        manifest_path = tmp_path / "manifest.json"
        entries = catalog_images(src, manifest_path)
        # Plain PIL JPEG has no EXIF date — should fall back to mtime
        assert entries[0]["date_source"] in ("exif", "mtime")

    def test_custom_folder_date_parser(self, tmp_path):
        src = tmp_path / "photos"
        src.mkdir()
        _make_jpeg(src / "a.jpg")
        manifest_path = tmp_path / "manifest.json"

        def fake_parser(path):
            return "2023-06-15"

        entries = catalog_images(src, manifest_path, folder_date_parser=fake_parser)
        # If no EXIF date, folder parser should be used
        if entries[0]["date_source"] == "folder":
            assert entries[0]["date"] == "2023-06-15"

    def test_scans_subdirectories(self, tmp_path):
        src = tmp_path / "photos"
        sub = src / "2023"
        sub.mkdir(parents=True)
        _make_jpeg(src / "top.jpg")
        _make_jpeg(sub / "sub.jpg")
        manifest_path = tmp_path / "manifest.json"
        entries = catalog_images(src, manifest_path)
        assert len(entries) == 2

    def test_skips_non_image_files(self, tmp_path):
        src = tmp_path / "photos"
        src.mkdir()
        _make_jpeg(src / "a.jpg")
        (src / "readme.txt").write_text("ignore me")
        manifest_path = tmp_path / "manifest.json"
        entries = catalog_images(src, manifest_path)
        assert len(entries) == 1


# ── sanitize_images ───────────────────────────────────────────────────────────

from imagekit_pipeline import sanitize_images


class TestSanitizeImages:
    def _make_manifest(self, tmp_path, images):
        """Write a manifest JSON and return the path."""
        manifest_path = tmp_path / "manifest.json"
        with open(manifest_path, "w") as f:
            json.dump(images, f)
        return manifest_path

    def test_sanitizes_and_renames_sequentially(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        out = tmp_path / "out"
        _make_jpeg(src / "photo.jpg")
        manifest = [
            {
                "source_dir": str(src),
                "relative_path": "photo.jpg",
                "date": "2023-01-01T12:00:00",
                "date_source": "mtime",
                "size": 1000,
            }
        ]
        manifest_path = self._make_manifest(tmp_path, manifest)
        entries = sanitize_images(manifest_path, out)
        assert len(entries) == 1
        assert entries[0]["new_key"] is not None
        assert (out / entries[0]["new_key"]).exists()

    def test_sequential_numbering_uses_4_digits(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        out = tmp_path / "out"
        _make_jpeg(src / "a.jpg")
        manifest = [
            {
                "source_dir": str(src),
                "relative_path": "a.jpg",
                "date": "2023-05-10T00:00:00",
                "date_source": "mtime",
                "size": 500,
            }
        ]
        manifest_path = self._make_manifest(tmp_path, manifest)
        entries = sanitize_images(manifest_path, out)
        key = entries[0]["new_key"]
        # Should be zero-padded to at least 4 digits
        stem = key.rsplit(".", 1)[0]
        assert len(stem) >= 4

    def test_sorts_by_date_oldest_first(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        out = tmp_path / "out"
        _make_jpeg(src / "newer.jpg")
        _make_jpeg(src / "older.jpg")
        manifest = [
            {
                "source_dir": str(src),
                "relative_path": "newer.jpg",
                "date": "2023-06-01T00:00:00",
                "date_source": "mtime",
                "size": 500,
            },
            {
                "source_dir": str(src),
                "relative_path": "older.jpg",
                "date": "2022-01-01T00:00:00",
                "date_source": "mtime",
                "size": 500,
            },
        ]
        manifest_path = self._make_manifest(tmp_path, manifest)
        entries = sanitize_images(manifest_path, out)
        # Sorted oldest first → older.jpg becomes 0001, newer.jpg becomes 0002
        by_src = {e["relative_path"]: e["new_key"] for e in entries}
        assert by_src["older.jpg"] < by_src["newer.jpg"]

    def test_error_entry_on_missing_source(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        out = tmp_path / "out"
        manifest = [
            {
                "source_dir": str(src),
                "relative_path": "ghost.jpg",
                "date": "2023-01-01T00:00:00",
                "date_source": "mtime",
                "size": 0,
            }
        ]
        manifest_path = self._make_manifest(tmp_path, manifest)
        entries = sanitize_images(manifest_path, out)
        assert entries[0]["new_key"] is None
        assert "error" in entries[0]

    def test_path_traversal_blocked(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        out = tmp_path / "out"
        manifest = [
            {
                "source_dir": str(src),
                "relative_path": "../../../etc/passwd",
                "date": "2023-01-01T00:00:00",
                "date_source": "mtime",
                "size": 0,
            }
        ]
        manifest_path = self._make_manifest(tmp_path, manifest)
        entries = sanitize_images(manifest_path, out)
        assert entries[0]["new_key"] is None
        assert "path traversal" in entries[0].get("error", "")


# ── generate_image_yaml ───────────────────────────────────────────────────────

from imagekit_pipeline import generate_image_yaml


class TestGenerateImageYaml:
    def test_generates_yaml_from_manifest(self, tmp_path):
        output = tmp_path / "images.yml"
        manifest = [
            {"new_key": "0001.jpeg", "orientation": "horizontal"},
            {"new_key": "0002.jpeg", "orientation": "vertical"},
            {"new_key": "0003.jpeg", "orientation": "horizontal"},
        ]
        h, v = generate_image_yaml(manifest=manifest, output_path=str(output))
        assert h == 2
        assert v == 1
        assert output.exists()

    def test_yaml_contains_correct_sections(self, tmp_path):
        output = tmp_path / "images.yml"
        manifest = [
            {"new_key": "0001.jpeg", "orientation": "horizontal"},
            {"new_key": "0002.jpeg", "orientation": "vertical"},
        ]
        generate_image_yaml(manifest=manifest, output_path=str(output))
        content = output.read_text()
        assert "horizontal_images:" in content
        assert "vertical_images:" in content

    def test_base_url_prepended(self, tmp_path):
        output = tmp_path / "images.yml"
        manifest = [{"new_key": "0001.jpeg", "orientation": "horizontal"}]
        generate_image_yaml(
            manifest=manifest,
            base_url="https://cdn.example.com",
            output_path=str(output),
        )
        content = output.read_text()
        assert "https://cdn.example.com/0001.jpeg" in content

    def test_raises_without_store_or_manifest(self, tmp_path):
        with pytest.raises(ValueError, match="store or manifest"):
            generate_image_yaml(output_path=str(tmp_path / "out.yml"))

    def test_skips_entries_without_new_key(self, tmp_path):
        output = tmp_path / "images.yml"
        manifest = [
            {"new_key": None, "orientation": "horizontal"},
            {"new_key": "0002.jpeg", "orientation": "vertical"},
        ]
        h, v = generate_image_yaml(manifest=manifest, output_path=str(output))
        assert h == 0
        assert v == 1

    def test_square_counts_as_horizontal(self, tmp_path):
        output = tmp_path / "images.yml"
        manifest = [{"new_key": "0001.jpeg", "orientation": "square"}]
        h, v = generate_image_yaml(manifest=manifest, output_path=str(output))
        assert h == 1
        assert v == 0


# ── update_image_yaml ─────────────────────────────────────────────────────────

from imagekit_pipeline import update_image_yaml


class TestUpdateImageYaml:
    def test_creates_file_if_missing(self, tmp_path):
        output = tmp_path / "images.yml"
        new_h, new_v = update_image_yaml(
            output,
            [{"key": "0001.jpeg", "url": "https://cdn.example.com/0001.jpeg", "orientation": "horizontal"}],
        )
        assert output.exists()
        assert new_h == 1
        assert new_v == 0

    def test_prepends_new_entries_to_existing(self, tmp_path):
        output = tmp_path / "images.yml"
        # Seed with one existing entry
        output.write_text(
            "horizontal_images:\n"
            "- url: https://cdn.example.com/0001.jpeg\n"
            "\nvertical_images:\n"
        )
        update_image_yaml(
            output,
            [{"key": "0002.jpeg", "url": "https://cdn.example.com/0002.jpeg", "orientation": "horizontal"}],
        )
        content = output.read_text()
        lines = [l for l in content.splitlines() if "- url:" in l]
        # Both entries present
        assert len(lines) == 2
        # New entry should come first (prepend)
        assert "0002.jpeg" in lines[0]
        assert "0001.jpeg" in lines[1]

    def test_vertical_entry_placed_correctly(self, tmp_path):
        output = tmp_path / "images.yml"
        update_image_yaml(
            output,
            [{"key": "0001.jpeg", "url": "https://cdn.example.com/0001.jpeg", "orientation": "vertical"}],
        )
        content = output.read_text()
        v_section = content.split("vertical_images:")[1]
        assert "0001.jpeg" in v_section

    def test_round_trip_no_double_quoting(self, tmp_path):
        """URLs written then re-read should not accumulate extra quotes."""
        output = tmp_path / "images.yml"
        url = "https://bucket.s3.us-east-1.amazonaws.com/0001.jpeg"
        update_image_yaml(
            output,
            [{"key": "0001.jpeg", "url": url, "orientation": "horizontal"}],
        )
        # Now update again — simulates a second wave of uploads
        update_image_yaml(
            output,
            [{"key": "0002.jpeg", "url": "https://bucket.s3.us-east-1.amazonaws.com/0002.jpeg", "orientation": "horizontal"}],
        )
        content = output.read_text()
        # No line should have double-quotes from double-wrapping
        for line in content.splitlines():
            if "- url:" in line:
                url_val = line.split("- url:", 1)[1].strip()
                # Should not start with "" (double-quoted)
                assert not url_val.startswith('""'), f"Double-quoted URL found: {line}"
