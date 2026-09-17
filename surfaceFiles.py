"""Flatten a directory tree into a separate destination without overwriting files."""
import argparse
import os
import re
import shutil
from pathlib import Path


def clean_name(name):
    name = re.sub(r'[a-f0-9]{32,}', '', name, flags=re.IGNORECASE)
    return re.sub(r'[^\w\s-]', '', name).strip() or 'unnamed'


def truncate_filename(filename, max_length=255):
    """Limit the UTF-8 byte length, preserving the extension."""
    if len(filename.encode('utf-8')) <= max_length:
        return filename
    stem, ext = os.path.splitext(filename)
    budget = max_length - len(ext.encode('utf-8'))
    if budget < 1:
        raise ValueError('Extension exceeds filename length limit')
    return stem.encode('utf-8')[:budget].decode('utf-8', errors='ignore') + ext


def process_files(src_folder, output_folder=None, *, extensions=None, group_depth=None):
    """Copy regular files; optionally group by a zero-based ancestor depth.

    By default all file types are copied into one flat directory. Symlinks are
    skipped. Existing destinations are preserved using numbered suffixes.
    """
    source = Path(src_folder).expanduser().resolve(strict=True)
    if not source.is_dir():
        raise NotADirectoryError(source)
    destination = (Path(output_folder).expanduser() if output_folder is not None
                   else source.with_name(source.name + '_Content')).resolve()
    if destination == source or source in destination.parents or destination in source.parents:
        raise ValueError('Source and destination must be separate, non-overlapping trees')
    if group_depth is not None and group_depth < 0:
        raise ValueError('group_depth must be nonnegative')
    selected = None if extensions is None else {'.' + e.lower().lstrip('.') for e in extensions}
    destination.mkdir(parents=True, exist_ok=True)
    copied = []
    for root, dirs, files in os.walk(source, followlinks=False):
        dirs[:] = sorted(d for d in dirs if not (Path(root) / d).is_symlink())
        for filename in sorted(files):
            path = Path(root) / filename
            if path.is_symlink() or not path.is_file():
                continue
            if selected is not None and path.suffix.lower() not in selected:
                continue
            parents = path.relative_to(source).parts[:-1]
            target_dir = destination
            if group_depth is not None and len(parents) > group_depth:
                target_dir /= clean_name(parents[group_depth])
                if target_dir.is_symlink():
                    raise ValueError('Destination group must not be a symbolic link')
                target_dir.mkdir(exist_ok=True)
            stem = '_'.join([clean_name(p) for p in parents] + [clean_name(path.stem)])
            number = 0
            while True:
                suffix = f' ({number})' if number else ''
                base = truncate_filename(stem + path.suffix, 255 - len(suffix))
                candidate = target_dir / (Path(base).stem + suffix + Path(base).suffix)
                try:
                    out = candidate.open('xb')
                except FileExistsError:
                    number += 1
                    continue
                try:
                    with out, path.open('rb') as inp:
                        shutil.copyfileobj(inp, out)
                except BaseException:
                    candidate.unlink()
                    raise
                copied.append(candidate)
                break
    return copied


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source')
    parser.add_argument('destination')
    parser.add_argument('--extensions', nargs='+', help='Only copy these extensions')
    parser.add_argument('--group-depth', type=int, help='Group by ancestor index (0 = top level)')
    args = parser.parse_args()
    copied = process_files(args.source, args.destination,
                           extensions=args.extensions, group_depth=args.group_depth)
    print(f'Copied {len(copied)} files')


if __name__ == '__main__':
    main()
