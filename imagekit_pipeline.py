"""
imagekit_pipeline — batch image processing pipelines.

Reusable functions for common image workflows: process local directories,
catalog images with EXIF dates, sanitize in bulk, upload to S3, and
generate image manifests.

All functions accept paths and config as parameters — no hardcoded
bucket names, directories, or site-specific values.

Usage:
    from imagekit_pipeline import process_local_images, catalog_images

    # Process a directory of images (strip metadata + generate web versions)
    process_local_images('photos/', 'photos/web/', max_width=1200)

    # Catalog images with EXIF dates for chronological sorting
    manifest = catalog_images('photos/', 'manifest.json')
"""

import json
import os
import shutil
import tempfile
import time
from datetime import datetime
from pathlib import Path

from imagekit import (strip_metadata, make_thumbnail, extract_exif_date,
                      get_orientation, is_image, needs_processing,
                      normalize_extension)


# ── Local image processing ────────────────────────────────────────────────

def find_images_to_process(source_dir, web_dir, force=False):
    """Find images in source_dir that need web versions in web_dir.

    Args:
        source_dir: Directory containing source images.
        web_dir: Directory for processed output images.
        force: If True, reprocess all images regardless of timestamps.

    Returns:
        List of Path objects for images that need processing.
    """
    source_dir = Path(source_dir)
    web_dir = Path(web_dir)

    if not source_dir.exists():
        return []

    to_process = []
    for img_path in sorted(source_dir.iterdir()):
        if not img_path.is_file() or not is_image(img_path):
            continue
        web_path = web_dir / img_path.name
        if force or needs_processing(img_path, web_path):
            to_process.append(img_path)

    return to_process


def process_local_images(source_dir, web_dir, max_width=1200, quality=80,
                         strip_quality=95, dry_run=False, force=False):
    """Strip metadata and generate web-optimized versions of images.

    Args:
        source_dir: Directory containing source images.
        web_dir: Directory for web-optimized output.
        max_width: Maximum width for web images.
        quality: JPEG quality for web images.
        strip_quality: JPEG quality when stripping metadata from originals.
        dry_run: If True, only print what would happen.
        force: If True, reprocess all images.

    Returns:
        Number of images processed.
    """
    source_dir = Path(source_dir)
    web_dir = Path(web_dir)
    images = find_images_to_process(source_dir, web_dir, force=force)

    if not images:
        return 0

    print(f'[imagekit] {len(images)} image(s) to process')

    if dry_run:
        for img in images:
            print(f'  Would process: {img.name}')
        return 0

    web_dir.mkdir(parents=True, exist_ok=True)
    start = time.time()
    processed = 0

    for img_path in images:
        if img_path.is_symlink():
            print(f'  SKIP {img_path.name}: symlink')
            continue
        web_path = web_dir / img_path.name
        if web_path.is_symlink():
            print(f'  SKIP {img_path.name}: output is symlink')
            continue
        try:
            w, h = strip_metadata(img_path, img_path, quality=strip_quality)
            tw, th = make_thumbnail(img_path, web_path,
                                    max_width=max_width, quality=quality)
            processed += 1
            print(f'  {img_path.name}: {w}x{h} -> {tw}x{th} web')
        except Exception as e:
            print(f'  ERROR {img_path.name}: {e}')

    elapsed = time.time() - start
    if processed:
        print(f'[imagekit] Processed {processed} image(s) in {elapsed:.1f}s')

    return processed


# ── Catalog + sanitize ────────────────────────────────────────────────────

def catalog_images(source_dir, manifest_path, folder_date_parser=None):
    """Scan a directory tree for images and build a manifest with EXIF dates.

    Args:
        source_dir: Root directory to scan recursively.
        manifest_path: Path to write the JSON manifest.
        folder_date_parser: Optional callable(Path) -> str that extracts a
            fallback ISO date from the folder structure. If None, uses
            the file modification time.

    Returns:
        List of manifest entries (also saved to manifest_path).
    """
    source_dir = Path(source_dir)
    manifest_path = Path(manifest_path)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
    all_files = []
    for root, dirs, files in os.walk(source_dir):
        dirs.sort()
        for fname in sorted(files):
            if os.path.splitext(fname)[1].lower() in image_extensions:
                all_files.append(Path(root) / fname)

    total = len(all_files)
    print(f'Found {total} images in {source_dir}/')

    manifest = []
    for i, filepath in enumerate(all_files):
        try:
            exif_date = extract_exif_date(filepath)
            exif_iso = exif_date.isoformat() if exif_date else None

            if exif_iso:
                date = exif_iso
                date_source = 'exif'
            elif folder_date_parser:
                date = folder_date_parser(filepath)
                date_source = 'folder'
            else:
                mtime = datetime.fromtimestamp(filepath.stat().st_mtime)
                date = mtime.isoformat()
                date_source = 'mtime'

            manifest.append({
                'source_dir': str(source_dir),
                'relative_path': str(filepath.relative_to(source_dir)),
                'date': date,
                'date_source': date_source,
                'size': filepath.stat().st_size,
            })
        except Exception as e:
            print(f'  WARN: skipping {filepath.name}: {e}')

        if (i + 1) % 100 == 0 or i + 1 == total:
            print(f'  Cataloged {i + 1}/{total}')

    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)

    exif_count = sum(1 for e in manifest if e['date_source'] == 'exif')
    print(f'Manifest saved: {exif_count}/{total} had EXIF dates')

    return manifest


def sanitize_images(manifest_path, output_dir, quality=95):
    """Strip metadata from all images in a manifest and rename sequentially.

    Reads the manifest, sorts by date (oldest first), strips metadata,
    and saves with sequential filenames (0001.jpeg, 0002.jpeg, ...).

    Args:
        manifest_path: Path to the JSON manifest from catalog_images().
        output_dir: Directory to write sanitized images.
        quality: JPEG quality for output images.

    Returns:
        Updated manifest entries (also saved back to manifest_path).
    """
    manifest_path = Path(manifest_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(manifest_path) as f:
        manifest = json.load(f)

    def _parse_date(entry):
        try:
            return datetime.fromisoformat(entry['date'])
        except (ValueError, TypeError):
            return datetime.min
    manifest.sort(key=_parse_date)
    total = len(manifest)
    digits = max(4, len(str(total)))
    errors = 0
    start = time.time()

    for i, entry in enumerate(manifest):
        seq = str(i + 1).zfill(digits)
        source_dir = Path(entry['source_dir']).resolve()
        local_path = (source_dir / entry['relative_path']).resolve()
        if not local_path.is_relative_to(source_dir):
            errors += 1
            entry['new_key'] = None
            entry['error'] = 'path traversal detected'
            print(f'\n  ERROR [{entry["relative_path"]}]: path traversal detected')
            continue
        ext = normalize_extension(local_path)
        out_name = f'{seq}{ext}'
        out_path = output_dir / out_name

        try:
            w, h = strip_metadata(local_path, out_path, quality=quality)
            entry['new_key'] = out_name
            entry['width'] = w
            entry['height'] = h
            entry['orientation'] = get_orientation(w, h)
        except Exception as e:
            errors += 1
            entry['new_key'] = None
            entry['error'] = str(e)
            print(f'\n  ERROR [{entry["relative_path"]}]: {e}')

        if (i + 1) % 50 == 0 or i + 1 == total:
            print(f'  Sanitized {i + 1}/{total}')

    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)

    elapsed = time.time() - start
    print(f'Done: {total - errors} sanitized, {errors} errors in {elapsed:.0f}s')

    return manifest


# ── S3 upload pipeline ────────────────────────────────────────────────────

def upload_new_photos(store, input_dir, uploaded_dir,
                      thumb_width=800, thumb_quality=80, full_quality=95,
                      dry_run=False):
    """Process new photos and upload to S3 with thumbnails.

    Args:
        store: An S3ImageStore instance.
        input_dir: Directory with photos to upload.
        uploaded_dir: Directory to move originals after upload.
        thumb_width: Maximum thumbnail width.
        thumb_quality: JPEG quality for thumbnails.
        full_quality: JPEG quality for full-res images.
        dry_run: If True, only preview.

    Returns:
        List of dicts with key, url, orientation, width, height for each
        uploaded image.

    Note:
        Not safe for concurrent use — sequential numbering assumes
        single-process execution.
    """
    input_dir = Path(input_dir)
    uploaded_dir = Path(uploaded_dir)

    if not input_dir.exists():
        input_dir.mkdir(parents=True, exist_ok=True)
        print(f'Created {input_dir}/ — drop photos there and re-run.')
        return []

    images = [f for f in sorted(input_dir.iterdir())
              if f.is_file() and not f.is_symlink() and is_image(f)]

    if not images:
        print(f'No images found in {input_dir}/')
        return []

    print(f'Found {len(images)} images to process.')

    if dry_run:
        for img in images:
            print(f'  Would process: {img.name}')
        return []

    uploaded_dir.mkdir(parents=True, exist_ok=True)
    tmp_dir = Path(tempfile.mkdtemp(prefix='imagekit-'))

    next_num = store.find_next_number()
    digits = max(4, len(str(next_num + len(images))))

    # Sort by EXIF date (oldest first)
    dated = []
    for img_path in images:
        try:
            date = extract_exif_date(img_path) or datetime.now()
        except Exception:
            date = datetime.now()
        dated.append((date, img_path))
    dated.sort(key=lambda x: x[0])

    entries = []
    start = time.time()

    for i, (date, img_path) in enumerate(dated):
        num = next_num + i
        seq = str(num).zfill(digits)
        ext = normalize_extension(img_path)
        key = f'{seq}{ext}'

        full_path = tmp_dir / f'full-{key}'
        thumb_path = tmp_dir / f'thumb-{key}'

        print(f'  [{i+1}/{len(dated)}] {img_path.name} -> {key}', end='', flush=True)

        uploaded_keys = []
        try:
            w, h = strip_metadata(img_path, full_path, quality=full_quality)
            orientation = get_orientation(w, h)
            make_thumbnail(full_path, thumb_path,
                           max_width=thumb_width, quality=thumb_quality)

            store.upload(full_path, key, width=w, height=h)
            uploaded_keys.append(key)
            store.upload(thumb_path, f'thumbs/{key}')
            uploaded_keys.append(f'thumbs/{key}')

            entries.append({
                'key': key,
                'url': store.url(key),
                'orientation': orientation,
                'width': w,
                'height': h,
            })

            dest = uploaded_dir / f'{seq}-{img_path.name}'
            if dest.exists():
                dest = uploaded_dir / f'{seq}-{int(time.time())}-{img_path.name}'
            shutil.move(str(img_path), str(dest))
            print(f'  {orientation} {w}x{h}')

        except Exception as e:
            print(f'  ERROR: {e}')
            for orphan_key in uploaded_keys:
                try:
                    store.client.delete_object(Bucket=store.bucket, Key=orphan_key)
                except Exception:
                    pass
        finally:
            full_path.unlink(missing_ok=True)
            thumb_path.unlink(missing_ok=True)

    shutil.rmtree(tmp_dir, ignore_errors=True)

    elapsed = time.time() - start
    print(f'Done in {elapsed:.0f}s. Uploaded {len(entries)}/{len(images)} images.')

    return entries


def _yaml_safe_url(url):
    """Strip control characters and quote if needed for safe YAML output."""
    url = ''.join(c for c in str(url) if c >= ' ' or c == '\t')
    if any(c in url for c in ':{}[],"\'|>&*!%#`@'):
        return f'"{url}"'
    return url


def _numeric_key(name):
    """Extract numeric prefix from a key name for sorting."""
    stem = os.path.splitext(os.path.basename(name))[0]
    try:
        return int(stem)
    except ValueError:
        return -1


# ── Manifest generation ───────────────────────────────────────────────────

def generate_image_yaml(store=None, manifest=None, base_url='',
                        output_path='_data/images.yml', newest_first=True):
    """Generate a YAML image manifest sorted by orientation.

    Provide either a store (reads from S3) or a manifest (list of dicts
    with 'new_key', 'orientation' fields from sanitize_images()).

    Args:
        store: Optional S3ImageStore to read images from.
        manifest: Optional list of manifest entries (from sanitize_images).
        base_url: Base URL prefix for manifest-based generation.
        output_path: Path to write the YAML file.
        newest_first: If True, sort newest images first.

    Returns:
        Tuple of (horizontal_count, vertical_count).
    """
    if store is None and manifest is None:
        raise ValueError('Either store or manifest must be provided')

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    horizontal = []
    vertical = []

    if store is not None:
        keys = store.list_images()
        keys.sort(key=_numeric_key, reverse=newest_first)
        print(f'Found {len(keys)} images. Reading dimensions...')

        for i, key in enumerate(keys):
            url = store.url(key)
            try:
                w, h = store.get_dimensions(key)
            except Exception as e:
                print(f'  WARN: skipping {key}: {e}')
                continue

            if w >= h:
                horizontal.append(url)  # horizontal + square
            else:
                vertical.append(url)

            if (i + 1) % 100 == 0 or i + 1 == len(keys):
                print(f'  Processed {i + 1}/{len(keys)}')

    elif manifest is not None:
        entries = [e for e in manifest if e.get('new_key')]
        entries.sort(key=lambda x: _numeric_key(x['new_key']), reverse=newest_first)

        for e in entries:
            url = f"{base_url}/{e['new_key']}" if base_url else e['new_key']
            if e.get('orientation') == 'vertical':
                vertical.append(url)
            else:
                horizontal.append(url)

    with open(output_path, 'w') as f:
        f.write('horizontal_images:\n')
        for url in horizontal:
            f.write(f'- url: {_yaml_safe_url(url)}\n')
        f.write('\nvertical_images:\n')
        for url in vertical:
            f.write(f'- url: {_yaml_safe_url(url)}\n')

    print(f'Generated {output_path}: {len(horizontal)} horizontal, {len(vertical)} vertical')
    return len(horizontal), len(vertical)


def update_image_yaml(output_path, new_entries):
    """Prepend new entries to an existing image YAML manifest.

    Args:
        output_path: Path to the YAML file.
        new_entries: List of dicts with 'key', 'url', 'orientation'.

    Returns:
        Tuple of (new_horizontal_count, new_vertical_count).
    """
    output_path = Path(output_path)
    horizontal = []
    vertical = []

    if output_path.exists():
        with open(output_path) as f:
            content = f.read()
        section = None
        for line in content.splitlines():
            stripped = line.strip()
            if stripped == 'horizontal_images:':
                section = 'h'
                continue
            elif stripped == 'vertical_images:':
                section = 'v'
                continue
            elif stripped.startswith('- url:'):
                url = stripped[len('- url:'):].strip()
                if section == 'h':
                    horizontal.append(url)
                elif section == 'v':
                    vertical.append(url)

    new_entries.sort(key=lambda e: _numeric_key(e.get('key', '')), reverse=True)
    new_h = [e['url'] for e in new_entries
             if e.get('orientation', 'horizontal') in ('horizontal', 'square')]
    new_v = [e['url'] for e in new_entries if e.get('orientation') == 'vertical']

    horizontal = new_h + horizontal
    vertical = new_v + vertical

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        f.write('horizontal_images:\n')
        for url in horizontal:
            f.write(f'- url: {_yaml_safe_url(url)}\n')
        f.write('\nvertical_images:\n')
        for url in vertical:
            f.write(f'- url: {_yaml_safe_url(url)}\n')

    return len(new_h), len(new_v)
