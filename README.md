# tidyData

**Created:** 2024-09-17
**Last Updated:** 2026-03-05

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

### combineMarkdown.py
Combines all Markdown (`.md`) files from a folder into a single file with headers.

### combinePDFS.py
Merges all PDF files from a folder into a single output PDF.

### combineTextFiles.py
Combines all text files from a folder into one file with delimiters.

### docSplice.py
Splits large documents into sections based on patterns.

### epubToMarkdown.py
Converts EPUB files to Markdown format.

### folderSizer.py
Analyzes folder sizes and file composition.

### surfaceFiles.py
Flattens nested folder structures by copying files with cleaned names.

## Installation

```sh
# Core (image processing + file utilities)
pip install git+https://github.com/sburl/tidyData.git

# With S3 support
pip install "tidydata[s3] @ git+https://github.com/sburl/tidyData.git"
```

## Dependencies

- `Pillow` — image processing
- `PyPDF2` — PDF handling
- `EbookLib` + `html2text` — EPUB conversion
- `boto3` — S3 storage (optional, install with `[s3]`)

## License
MIT License.
