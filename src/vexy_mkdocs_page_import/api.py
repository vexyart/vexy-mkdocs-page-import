# this_file: src/vexy_mkdocs_page_import/api.py
"""Fetch source HTML and work with its cache and metadata without starting a site build."""

import hashlib
from collections.abc import Mapping
from pathlib import Path
from tempfile import TemporaryDirectory

_IMPORT_KEYS = ("import-url", "webflow-import-url", "copy-file")
_DEFAULT_RETRIES = 2
DEFAULT_MAX_BYTES = 20 * 1024 * 1024


def fetch_url(
    url: str,
    *,
    timeout: float = 30,
    retries: int = _DEFAULT_RETRIES,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> str:
    """Download decoded HTML without caching. Retries count additional attempts."""
    from ._download import download  # noqa: PLC0415 -- keep cache helpers dependency-free

    return download(url, timeout, retries, max_bytes)


def cache_path(cache_dir: Path, url: str) -> Path:
    """Return the cache file for the exact URL, without touching the filesystem."""
    key = hashlib.sha256(url.encode("utf-8")).hexdigest()
    return cache_dir / f"{key}.html"


def _store(path: Path, html: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=path.parent) as temp:
        staged = Path(temp) / path.name
        staged.write_bytes(html.encode("utf-8"))
        staged.replace(path)


def refresh_cache(
    url: str,
    cache_dir: Path,
    *,
    timeout: float = 30,
    retries: int = _DEFAULT_RETRIES,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> str:
    """Fetch source HTML and atomically replace its cache entry after a successful download."""
    html = fetch_url(url, timeout=timeout, retries=retries, max_bytes=max_bytes)
    _store(cache_path(cache_dir, url), html)
    return html


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
