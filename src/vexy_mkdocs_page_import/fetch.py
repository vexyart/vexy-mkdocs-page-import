# this_file: src/vexy_mkdocs_page_import/fetch.py
"""Read remote HTML, caching the source before any page-specific edits."""

from pathlib import Path

from mkdocs.exceptions import PluginError
from mkdocs.plugins import get_plugin_logger

from ._urls import checked_url, display_url
from .api import _store, cache_path, fetch_url, read_cached
from .config import PageImportConfig

log = get_plugin_logger(__name__)


def fetch(url: str, config_dir: Path, options: PageImportConfig) -> str | None:
    """Return source HTML, or None when an offline miss should keep the rendered page."""
    label = display_url(checked_url(url))
    cache_dir = config_dir / options.cache_dir
    if options.offline or not options.refresh:
        if (cached := read_cached(cache_dir, url)) is not None:
            return cached
        if options.offline:
            if options.on_offline_miss == "keep":
                return None
            raise PluginError(f"offline cache miss for {label}")
    try:
        html = fetch_url(url, timeout=options.timeout, max_bytes=options.max_bytes)
    except OSError as exc:
        if (cached := read_cached(cache_dir, url)) is None:
            log.warning("%s; no cached copy available", exc)
            raise PluginError(str(exc)) from exc
        log.info("%s; serving cached copy", exc)
        return cached
    _store(cache_path(cache_dir, url), html)
    return html
