"""Shared path handling for standalone file utilities."""
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path


def input_files(folder, output, extensions):
    folder = Path(folder).expanduser().resolve(strict=True)
    if not folder.is_dir():
        raise NotADirectoryError(folder)
    output = Path(output).expanduser()
    if not output.is_absolute():
        output = folder / output
    if output.is_symlink():
        raise ValueError('Output must not be a symbolic link')
    output = output.resolve()
    files = [p for p in sorted(folder.iterdir())
             if p.is_file() and not p.is_symlink()
             and p.suffix.lower() in extensions and p.resolve() != output
             and not (output.exists() and p.samefile(output))]
    if not files:
        raise ValueError('No matching input files')
    return files, output


@contextmanager
def atomic_output(output, binary=False):
    """Replace output only after a successful write; leave inputs intact on failure."""
    output = Path(output)
    fd, name = tempfile.mkstemp(prefix='.tidydata-', dir=output.parent)
    try:
        with os.fdopen(fd, 'wb' if binary else 'w',
                       **({} if binary else {'encoding': 'utf-8'})) as stream:
            yield stream
        os.replace(name, output)
    finally:
        if os.path.exists(name):
            os.unlink(name)
