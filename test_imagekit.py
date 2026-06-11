"""
Unit tests for imagekit.py — pure-logic helpers that do not require Pillow
are tested without it; functions that use PIL are tested with a real in-memory
JPEG produced by Pillow (available in the project's requirements).
"""
import io
import os
import tempfile
from pathlib import Path

import pytest

# ── helpers that don't touch PIL ─────────────────────────────────────────────

from imagekit import is_image, normalize_extension, needs_processing


class TestIsImage:
    def test_jpg_lowercase(self):
        assert is_image("photo.jpg") is True

    def test_jpeg_lowercase(self):
        assert is_image("photo.jpeg") is True

    def test_png(self):
        assert is_image("photo.png") is True

    def test_gif(self):
        assert is_image("photo.gif") is True

    def test_webp(self):
        assert is_image("photo.webp") is True

    def test_uppercase_extension(self):
        # extension comparison is case-insensitive
        assert is_image("photo.JPG") is True

    def test_txt_not_image(self):
        assert is_image("document.txt") is False

    def test_pdf_not_image(self):
        assert is_image("file.pdf") is False

    def test_no_extension(self):
        assert is_image("noextension") is False


class TestNormalizeExtension:
    def test_jpg_becomes_jpeg(self):
        assert normalize_extension("photo.jpg") == ".jpeg"

    def test_jpeg_stays_jpeg(self):
        assert normalize_extension("photo.jpeg") == ".jpeg"

    def test_png_unchanged(self):
        assert normalize_extension("photo.png") == ".png"

    def test_webp_unchanged(self):
        assert normalize_extension("photo.webp") == ".webp"

    def test_uppercase_jpg(self):
        assert normalize_extension("photo.JPG") == ".jpeg"


class TestNeedsProcessing:
    def test_dst_missing_means_needs_processing(self, tmp_path):
        src = tmp_path / "src.jpg"
        src.write_bytes(b"fake")
        dst = tmp_path / "dst.jpg"
        # dst does not exist
        assert needs_processing(src, dst) is True

    def test_dst_exists_and_newer_means_no_processing(self, tmp_path):
        src = tmp_path / "src.jpg"
        dst = tmp_path / "dst.jpg"
        src.write_bytes(b"fake")
        dst.write_bytes(b"processed")
        # make dst newer than src
        os.utime(dst, (src.stat().st_mtime + 10, src.stat().st_mtime + 10))
        assert needs_processing(src, dst) is False

    def test_src_newer_than_dst_means_needs_processing(self, tmp_path):
        src = tmp_path / "src.jpg"
        dst = tmp_path / "dst.jpg"
        dst.write_bytes(b"old")
        src.write_bytes(b"new")
        # make src newer
        os.utime(src, (dst.stat().st_mtime + 10, dst.stat().st_mtime + 10))
        assert needs_processing(src, dst) is True


# ── Pillow-dependent tests ────────────────────────────────────────────────────

PIL = pytest.importorskip("PIL", reason="Pillow not installed — skipping image I/O tests")

from PIL import Image
from imagekit import strip_metadata, make_thumbnail, get_dimensions as get_image_size


def _make_jpeg(path: Path, width=100, height=80, color=(200, 100, 50)):
    """Write a minimal RGB JPEG to path and return the path."""
    img = Image.new("RGB", (width, height), color=color)
    img.save(str(path), "JPEG", quality=85)
    return path


class TestStripMetadata:
    def test_output_file_created(self, tmp_path):
        src = _make_jpeg(tmp_path / "src.jpg")
        dst = tmp_path / "dst.jpg"
        strip_metadata(src, dst)
        assert dst.exists()

    def test_returns_dimensions(self, tmp_path):
        src = _make_jpeg(tmp_path / "src.jpg", width=120, height=90)
        dst = tmp_path / "dst.jpg"
        w, h = strip_metadata(src, dst)
        assert w == 120
        assert h == 90

    def test_output_is_valid_image(self, tmp_path):
        src = _make_jpeg(tmp_path / "src.jpg")
        dst = tmp_path / "dst.jpg"
        strip_metadata(src, dst)
        with Image.open(dst) as img:
            assert img.format == "JPEG"

    def test_creates_parent_dirs(self, tmp_path):
        src = _make_jpeg(tmp_path / "src.jpg")
        dst = tmp_path / "nested" / "deep" / "dst.jpg"
        strip_metadata(src, dst)
        assert dst.exists()

    def test_png_round_trip(self, tmp_path):
        src = tmp_path / "src.png"
        img = Image.new("RGB", (50, 50), color=(10, 20, 30))
        img.save(str(src), "PNG")
        dst = tmp_path / "dst.png"
        w, h = strip_metadata(src, dst)
        assert w == 50 and h == 50
        assert dst.exists()


class TestMakeThumbnail:
    def test_wide_image_resized(self, tmp_path):
        src = _make_jpeg(tmp_path / "wide.jpg", width=1600, height=1200)
        dst = tmp_path / "thumb.jpg"
        w, h = make_thumbnail(src, dst, max_width=800)
        assert w == 800
        assert h == 600  # proportional

    def test_small_image_not_upscaled(self, tmp_path):
        src = _make_jpeg(tmp_path / "small.jpg", width=400, height=300)
        dst = tmp_path / "thumb.jpg"
        w, h = make_thumbnail(src, dst, max_width=800)
        assert w == 400
        assert h == 300

    def test_output_file_created(self, tmp_path):
        src = _make_jpeg(tmp_path / "src.jpg")
        dst = tmp_path / "thumb.jpg"
        make_thumbnail(src, dst)
        assert dst.exists()


class TestGetImageSize:
    def test_returns_correct_size(self, tmp_path):
        src = _make_jpeg(tmp_path / "img.jpg", width=320, height=240)
        w, h = get_image_size(src)
        assert w == 320
        assert h == 240
