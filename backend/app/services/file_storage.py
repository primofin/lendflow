"""Local-disk file store for uploads. Keys are server-generated; paths cannot leave the root."""

import os
from pathlib import Path

from app.core.config import get_settings


def _root() -> Path:
    return Path(get_settings().storage_dir).resolve()


def _path(key: str) -> Path:
    root = _root()
    path = (root / key).resolve()
    if root not in path.parents:  # defence in depth: keys are generated, never user input
        raise ValueError("Storage key escapes the storage folder")
    return path


def save(key: str, data: bytes) -> None:
    """Write atomically (temp file, then rename) with owner-only permissions."""
    path = _path(key)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temp = path.with_name(path.name + ".tmp")
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        os.replace(temp, path)
    except BaseException:
        temp.unlink(missing_ok=True)
        raise


def read(key: str) -> bytes:
    return _path(key).read_bytes()


def delete(key: str) -> None:
    _path(key).unlink(missing_ok=True)
