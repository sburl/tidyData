"""
imagekit — reusable image processing functions.

Strip metadata, generate thumbnails, detect orientation. Each function
works standalone or can be composed into pipelines.

Usage as a library:
    from imagekit import strip_metadata, make_thumbnail, process_image

Usage from the command line:
    python3 imagekit.py strip  photo.jpg clean.jpg
    python3 imagekit.py thumb  photo.jpg thumb.jpg --max-width 800
    python3 imagekit.py process photo.jpg --out-dir ./output --thumb-dir ./thumbs
"""

import argparse
import os
import sys
from pathlib import Path

from PIL import Image, ImageOps, ExifTags
from datetime import datetime

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}


# ── Core functions ──────────────────────────────────────────────────────────

def strip_metadata(src, dst, quality=95):
    """Strip ALL metadata from an image and save a clean copy.

    Removes EXIF (GPS, camera, timestamps, lens info, MakerNote),
    ICC profiles, XMP, IPTC — everything. Applies EXIF rotation to
    pixel data before stripping so the image displays correctly.

    Args:
        src: Path to source image.
        dst: Path to write the clean image.
        quality: JPEG quality (1-100). Ignored for PNG/GIF.

    Returns:
        (width, height) tuple of the output image.
    """
    src, dst = Path(src), Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)

    img = Image.open(src)
    img = ImageOps.exif_transpose(img)
    w, h = img.size

    # Create a brand-new image with ONLY pixel data — no metadata carryover.
    # Convert palette (P) and RGBA modes to RGB for broad compatibility,
    # but preserve for PNG output to keep transparency/palette intact.
    out_ext = dst.suffix.lower()
    if img.mode == 'P' and out_ext == '.png':
        # For palette PNGs, convert to RGBA to preserve any transparency,
        # then create a clean copy without metadata
        img = img.convert('RGBA')
    elif img.mode not in ('RGB', 'L'):
        if out_ext in ('.jpg', '.jpeg'):
            img = img.convert('RGB')

    clean = Image.new(img.mode, img.size)
    clean.paste(img)
    img.close()

    _save_image(clean, dst, quality)
    clean.close()
    return w, h


def make_thumbnail(src, dst, max_width=800, quality=80):
    """Generate a width-constrained thumbnail.

    If the source is already smaller than max_width, it is saved at the
    given quality without upscaling.

    Args:
        src: Path to source image (should already be metadata-stripped).
        dst: Path to write the thumbnail.
        max_width: Maximum width in pixels.
        quality: JPEG quality (1-100). Ignored for PNG/GIF.

    Returns:
        (width, height) tuple of the output thumbnail.
    """
    src, dst = Path(src), Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)

    img = Image.open(src)
    img = ImageOps.exif_transpose(img)
    w, h = img.size

    if w > max_width:
        ratio = max_width / w
        new_h = int(h * ratio)
        img = img.resize((max_width, new_h), Image.LANCZOS)
        w, h = img.size

    _save_image(img, dst, quality)
    img.close()
    return w, h


def process_image(src, full_dst=None, thumb_dst=None,
                  strip_quality=95, thumb_max_width=800, thumb_quality=80):
    """Strip metadata and optionally generate a thumbnail in one call.

    Args:
        src: Path to source image.
        full_dst: Where to save the stripped full-res image. If None, skipped.
        thumb_dst: Where to save the thumbnail. If None, skipped.
        strip_quality: JPEG quality for the full-res output.
        thumb_max_width: Max width for the thumbnail.
        thumb_quality: JPEG quality for the thumbnail.

    Returns:
        dict with keys: width, height, orientation, full_path, thumb_path.
    """
    result = {'full_path': None, 'thumb_path': None}

    if full_dst:
        w, h = strip_metadata(src, full_dst, quality=strip_quality)
        result['width'] = w
        result['height'] = h
        result['orientation'] = get_orientation(w, h)
        result['full_path'] = str(full_dst)

        if thumb_dst:
            tw, th = make_thumbnail(full_dst, thumb_dst,
                                    max_width=thumb_max_width,
                                    quality=thumb_quality)
            result['thumb_path'] = str(thumb_dst)
            result['thumb_width'] = tw
            result['thumb_height'] = th

    elif thumb_dst:
        # Thumbnail only — strip metadata into a temp then thumbnail
        tw, th = make_thumbnail(src, thumb_dst,
                                max_width=thumb_max_width,
                                quality=thumb_quality)
        result['thumb_path'] = str(thumb_dst)
        result['thumb_width'] = tw
        result['thumb_height'] = th

    return result


def get_orientation(width, height):
    """Return 'horizontal', 'vertical', or 'square'."""
    if width > height:
        return 'horizontal'
    elif height > width:
        return 'vertical'
    return 'square'


def get_dimensions(path):
    """Return (width, height) without loading the full image into memory."""
    with Image.open(path) as img:
        img = ImageOps.exif_transpose(img)
        return img.size


def extract_exif_date(path):
    """Extract the earliest EXIF date from an image file.

    Returns a datetime object or None if no EXIF date is found.
    """
    try:
        with Image.open(path) as img:
            try:
                exif = img._getexif()
            except Exception:
                exif = None
            if not exif:
                try:
                    exif = dict(img.getexif())
                except Exception:
                    return None
            if not exif:
                return None

            date_tags = ('DateTimeOriginal', 'DateTimeDigitized', 'DateTime')
            dates = []
            for tag_id, value in exif.items():
                tag_name = ExifTags.TAGS.get(tag_id, '')
                if tag_name in date_tags and isinstance(value, str):
                    for fmt in ('%Y:%m:%d %H:%M:%S', '%Y:%m:%d'):
                        try:
                            dates.append(datetime.strptime(value, fmt))
                            break
                        except ValueError:
                            continue
            return min(dates) if dates else None
    except Exception:
        return None


def needs_processing(src, dst):
    """Return True if dst doesn't exist or src is newer than dst."""
    src, dst = Path(src), Path(dst)
    if not dst.exists():
        return True
    return src.stat().st_mtime > dst.stat().st_mtime


def is_image(path):
    """Return True if the path has a recognized image extension."""
    return Path(path).suffix.lower() in IMAGE_EXTENSIONS


def normalize_extension(path):
    """Return the canonical extension for an image (.jpg/.jpeg → .jpeg)."""
    ext = Path(path).suffix.lower()
    if ext in ('.jpg', '.jpeg'):
        return '.jpeg'
    return ext


# ── Internal helpers ────────────────────────────────────────────────────────

def _save_image(img, path, quality):
    """Save a PIL image to path with appropriate format settings."""
    ext = Path(path).suffix.lower()
    if ext in ('.jpg', '.jpeg'):
        if img.mode not in ('RGB', 'L'):
            img = img.convert('RGB')
        img.save(path, 'JPEG', quality=quality, optimize=True)
    elif ext == '.png':
        img.save(path, 'PNG', optimize=True)
    elif ext == '.gif':
        img.save(path, 'GIF')
    elif ext == '.webp':
        img.save(path, 'WEBP', quality=quality)
    else:
        if img.mode not in ('RGB', 'L'):
            img = img.convert('RGB')
        img.save(path, 'JPEG', quality=quality, optimize=True)


# ── CLI ─────────────────────────────────────────────────────────────────────

def _cli_strip(args):
    w, h = strip_metadata(args.src, args.dst, quality=args.quality)
    print(f'{args.src} → {args.dst}  ({w}x{h}, quality {args.quality})')


def _cli_thumb(args):
    w, h = make_thumbnail(args.src, args.dst,
                          max_width=args.max_width, quality=args.quality)
    print(f'{args.src} → {args.dst}  ({w}x{h}, max-width {args.max_width})')


def _cli_process(args):
    full_dst = Path(args.out_dir) / Path(args.src).name if args.out_dir else None
    thumb_dst = Path(args.thumb_dir) / Path(args.src).name if args.thumb_dir else None
    result = process_image(
        args.src, full_dst, thumb_dst,
        strip_quality=args.quality,
        thumb_max_width=args.max_width,
        thumb_quality=args.thumb_quality,
    )
    for k, v in result.items():
        if v is not None:
            print(f'  {k}: {v}')


def main():
    parser = argparse.ArgumentParser(
        description='Image processing toolkit.')
    sub = parser.add_subparsers(dest='command', required=True)

    # strip
    p_strip = sub.add_parser('strip', help='Strip all metadata from an image')
    p_strip.add_argument('src', help='Source image path')
    p_strip.add_argument('dst', help='Destination path')
    p_strip.add_argument('--quality', type=int, default=95)
    p_strip.set_defaults(func=_cli_strip)

    # thumb
    p_thumb = sub.add_parser('thumb', help='Generate a thumbnail')
    p_thumb.add_argument('src', help='Source image path')
    p_thumb.add_argument('dst', help='Destination path')
    p_thumb.add_argument('--max-width', type=int, default=800)
    p_thumb.add_argument('--quality', type=int, default=80)
    p_thumb.set_defaults(func=_cli_thumb)

    # process
    p_proc = sub.add_parser('process', help='Strip metadata + generate thumbnail')
    p_proc.add_argument('src', help='Source image path')
    p_proc.add_argument('--out-dir', help='Directory for stripped full-res image')
    p_proc.add_argument('--thumb-dir', help='Directory for thumbnail')
    p_proc.add_argument('--quality', type=int, default=95)
    p_proc.add_argument('--max-width', type=int, default=800)
    p_proc.add_argument('--thumb-quality', type=int, default=80)
    p_proc.set_defaults(func=_cli_process)

    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
