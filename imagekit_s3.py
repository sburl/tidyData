"""
imagekit_s3 — S3 image storage helpers.

Parameterized wrapper around boto3 for uploading, listing, and managing
images in an S3 bucket. Works with imagekit for metadata stripping and
thumbnail generation.

Usage:
    from imagekit_s3 import S3ImageStore

    store = S3ImageStore(bucket='my-images', region='us-east-1')
    store.upload('local.jpg', '0001.jpeg', width=1920, height=1080)
    store.upload('thumb.jpg', 'thumbs/0001.jpeg')
    images = store.list_images()
"""

import os
from pathlib import Path
from urllib.parse import quote


CONTENT_TYPES = {
    '.jpeg': 'image/jpeg',
    '.jpg': 'image/jpeg',
    '.png': 'image/png',
    '.gif': 'image/gif',
    '.webp': 'image/webp',
}


class S3ImageStore:
    """Parameterized S3 image storage."""

    def __init__(self, bucket, region='us-east-1'):
        self.bucket = bucket
        self.region = region
        self.base_url = f'https://{bucket}.s3.{region}.amazonaws.com'
        self._client = None

    @property
    def client(self):
        if self._client is None:
            import boto3
            self._client = boto3.client('s3', region_name=self.region)
        return self._client

    def upload(self, local_path, key, width=None, height=None):
        """Upload an image to S3 with optional dimension metadata."""
        ext = os.path.splitext(key)[1].lower()
        content_type = CONTENT_TYPES.get(ext, 'image/jpeg')

        extra = {'ContentType': content_type}
        if width is not None and height is not None:
            extra['Metadata'] = {'width': str(width), 'height': str(height)}

        self.client.upload_file(str(local_path), self.bucket, key, ExtraArgs=extra)

    def url(self, key):
        """Return the public URL for an S3 key."""
        return f'{self.base_url}/{quote(key, safe="/")}'

    def find_next_number(self):
        """Find the highest-numbered image in the bucket and return next number."""
        paginator = self.client.get_paginator('list_objects_v2')
        max_num = 0
        for page in paginator.paginate(Bucket=self.bucket):
            for obj in page.get('Contents', []):
                basename = os.path.basename(obj['Key'])
                name = os.path.splitext(basename)[0]
                try:
                    max_num = max(max_num, int(name))
                except ValueError:
                    continue
        return max_num + 1

    def list_images(self, extensions=None):
        """List all image keys in the bucket (excluding thumbs/ prefix)."""
        if extensions is None:
            extensions = ('.jpg', '.jpeg', '.png', '.gif', '.webp')
        paginator = self.client.get_paginator('list_objects_v2')
        keys = []
        for page in paginator.paginate(Bucket=self.bucket):
            for obj in page.get('Contents', []):
                key = obj['Key']
                if key.startswith('thumbs/'):
                    continue
                if key.lower().endswith(tuple(extensions)):
                    keys.append(key)
        return keys

    def get_dimensions(self, key):
        """Get (width, height) from S3 metadata, downloading as fallback."""
        head = self.client.head_object(Bucket=self.bucket, Key=key)
        metadata = head.get('Metadata', {})
        try:
            width = int(metadata.get('width', 0))
            height = int(metadata.get('height', 0))
        except (ValueError, TypeError):
            width, height = 0, 0

        if width == 0 or height == 0:
            from PIL import Image
            from io import BytesIO
            response = self.client.get_object(Bucket=self.bucket, Key=key)
            body = response['Body']
            try:
                img = Image.open(BytesIO(body.read()))
                width, height = img.size
                img.close()
            finally:
                body.close()

        return width, height

    def count_objects(self):
        """Count total objects in the bucket."""
        paginator = self.client.get_paginator('list_objects_v2')
        total = 0
        for page in paginator.paginate(Bucket=self.bucket):
            total += len(page.get('Contents', []))
        return total

    def delete_all(self, confirm=True):
        """Delete all objects from the bucket.

        Args:
            confirm: If True, prompts for interactive confirmation.

        Returns:
            Number of objects deleted.
        """
        total = self.count_objects()
        if total == 0:
            print('Bucket is already empty.')
            return 0

        print(f'Found {total} objects to delete.')

        if confirm:
            response = input(f"\nType 'delete {total} objects' to proceed: ")
            if response != f'delete {total} objects':
                print('Aborted.')
                return 0

        paginator = self.client.get_paginator('list_objects_v2')
        deleted = 0
        for page in paginator.paginate(Bucket=self.bucket):
            contents = page.get('Contents', [])
            if not contents:
                continue
            batch = [{'Key': o['Key']} for o in contents]
            self.client.delete_objects(Bucket=self.bucket, Delete={'Objects': batch})
            deleted += len(batch)

        return deleted
