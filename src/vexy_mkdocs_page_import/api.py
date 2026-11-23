# this_file: src/vexy_mkdocs_page_import/api.py
"""Inspect import metadata and the source HTML cache without starting a site build."""

import hashlib
from collections.abc import Mapping
from pathlib import Path

_IMPORT_KEYS = ("import-url", "webflow-import-url", "copy-file")


def cache_path(cache_dir: Path, url: str) -> Path:
    """Return the cache file for the exact URL, without touching the filesystem."""
    key = hashlib.sha256(url.encode("utf-8")).hexdigest()
    return cache_dir / f"{key}.html"


def read_cached(cache_dir: Path, url: str) -> str | None:
    """Read cached source HTML, returning None for missing or unusable entries."""
    path = cache_path(cache_dir, url)
    try:
        if not path.is_file():
            return None
        html = path.read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    return html if html.strip() else None


def import_keys(meta: Mapping[str, object]) -> tuple[str, str] | None:
    """Return the single import key and value, raising ValueError for invalid metadata."""
    keys = [key for key in _IMPORT_KEYS if key in meta]
    if not keys:
        return None
    if len(keys) > 1:
        raise ValueError(f"specify only one import key; found {', '.join(keys)}")
    key = keys[0]
    source = meta[key]
    if not isinstance(source, str) or not source.strip():
        raise ValueError(f"{key} requires a non-empty string")
    return key, source
