# tidyData

**Created:** 2024-09-17
**Last Updated:** 2026-09-16

**tidyData** is a collection of Python utilities for data tidying, file management, and image privacy. Strip metadata from photos, generate thumbnails, batch-process directories, and upload to S3 — all with simple library calls or CLI commands.

## Image Privacy Toolkit

### imagekit.py — Core Image Processing

Strip metadata, generate thumbnails, detect orientation, and extract EXIF dates. Works as both a library and a CLI tool. Supports JPEG, PNG, GIF, and WebP.

**As a library:**
```python
from imagekit import strip_metadata, make_thumbnail, process_image

# Strip ALL metadata (GPS, camera, timestamps, EXIF, XMP, ICC, IPTC)
strip_metadata("photo.jpg", "clean.jpg")

# Generate a width-constrained thumbnail
make_thumbnail("photo.jpg", "thumb.jpg", max_width=800)

# Combined: strip + thumbnail in one call
result = process_image("photo.jpg", full_dst="clean.jpg", thumb_dst="thumb.jpg")
```

**From the command line:**
```sh
python3 imagekit.py strip photo.jpg clean.jpg
python3 imagekit.py thumb photo.jpg thumb.jpg --max-width 800
python3 imagekit.py process photo.jpg --out-dir ./output --thumb-dir ./thumbs
```

### imagekit_pipeline.py — Batch Processing

Reusable pipelines for directory-level image processing. All functions accept paths and config as parameters — no hardcoded values.

```python
from imagekit_pipeline import process_local_images, catalog_images, sanitize_images

# Process a directory: strip metadata + generate web-optimized versions
process_local_images('photos/', 'photos/web/', max_width=1200, quality=80)

# Catalog images with EXIF dates for chronological sorting
catalog_images('photos/', 'manifest.json')

# Strip metadata and rename sequentially (0001.jpeg, 0002.jpeg, ...)
sanitize_images('manifest.json', 'sanitized/')
```

### imagekit_s3.py — S3 Image Storage

Parameterized S3 wrapper for uploading, listing, and managing images. Requires `boto3` (install with `pip install tidydata[s3]`).

```python
from imagekit_s3 import S3ImageStore
from imagekit_pipeline import upload_new_photos, generate_image_yaml

store = S3ImageStore(bucket='my-images', region='us-east-1')

# Upload new photos with metadata stripping + thumbnails
entries = upload_new_photos(
    store,
    input_dir='to-upload/',
    uploaded_dir='uploaded/',
    thumb_width=800,
)

# Generate a YAML manifest from S3 bucket contents
generate_image_yaml(store=store, output_path='images.yml')
```

## File Management Utilities

All modules are safe to import. File paths and split markers are supplied at runtime;
no utility defaults to a personal Downloads folder or document.

```sh
python -m combineMarkdown ./notes -o combined.md
python -m combinePDFS ./pdfs -o combined.pdf
python -m combineTextFiles ./notes -o combined.txt --extensions txt md
python -m docSplice input.docx "First marker" "Second marker" part1.docx part2.docx part3.docx
python -m epubToMarkdown ./books ./markdown
python -m folderSizer ./files --min-size 0 -o report.txt
python -m surfaceFiles ./export ./flattened
```

The combiners process regular, non-symlink files in filename order. Output paths
are relative to the input folder unless absolute. Existing combined output is
excluded from inputs and replaced only after a successful write. Text must be
UTF-8; a decoding failure leaves the previous output intact. Text output contains
filenames, not absolute paths. Contents and filenames themselves are not redacted.
PDF merging does not guarantee compression.

`folderSizer` skips symbolic links so reports stay within the selected tree.

`docSplice` requires two markers in order in separate paragraphs and three distinct,
new output paths. It copies paragraph text only, not document formatting or tables.

`surfaceFiles` defaults to all regular file types and a flat destination. Source
and destination trees must not overlap; symlinks are skipped. It cleans hashes
and punctuation from names, includes relative ancestor names, and adds numbered
suffixes on collision instead of overwriting. Names are limited by UTF-8 bytes.
Repeated runs create additional numbered copies. This copies file contents; it
does not strip metadata embedded in attachments. Use `imagekit` for image privacy.

To filter attachments or retain groups, opt in explicitly:

```sh
python -m surfaceFiles ./export ./attachments --extensions jpg png pdf
python -m surfaceFiles ./export ./grouped --group-depth 1
```

`--group-depth 0` uses the top-level ancestor; `1` uses the next level, as in an
export with a wrapper folder above its categories. There are no prescribed PARA
category names. Files without that ancestor stay at the destination root.

**Migration:** `process_files(source)` now writes to a sibling `source_Content`
folder, copies all regular file types, and uses a flat layout by default. Pass an
explicit output folder, `extensions`, and `group_depth` to reproduce a particular
export layout. No scripts execute on import or use hardcoded example paths.

## Development

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[s3]" pytest
python -m pytest
```

Virtual environments are local and ignored, not distributed with the repository.
The build backend minimum supports the advertised Python 3.9 baseline and the
project’s license metadata; it is not tied to one developer’s installed version.

## Installation

```sh
# Core (image processing + file utilities)
pip install git+https://github.com/sburl/tidyData.git

# With S3 support
pip install "tidydata[s3] @ git+https://github.com/sburl/tidyData.git"
```

## Dependencies

- `Pillow` — image processing
- `pypdf` — PDF handling
- `EbookLib` + `html2text` — EPUB conversion
- `boto3` — S3 storage (optional, install with `[s3]`)

## License
MIT License.
