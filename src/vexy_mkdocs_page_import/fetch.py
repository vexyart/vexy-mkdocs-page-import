# this_file: src/vexy_mkdocs_page_import/fetch.py
"""Read remote HTML, caching the source before any page-specific edits."""

import hashlib
import time
from http.client import HTTPException, HTTPMessage
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import IO, override
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from mkdocs.exceptions import PluginError
from mkdocs.plugins import get_plugin_logger

from .config import PageImportConfig

log = get_plugin_logger(__name__)
ATTEMPTS = 3
HTTP_SCHEMES = {"http", "https"}


class _HTTPRedirects(HTTPRedirectHandler):
    @override
    def redirect_request(
        self, req: Request, fp: IO[bytes], code: int, msg: str, headers: HTTPMessage, newurl: str
    ) -> Request | None:
        if urlsplit(newurl).scheme not in HTTP_SCHEMES:
            raise HTTPError(newurl, code, f"Refused redirect to {newurl}", headers, fp)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _download(url: str, timeout: float) -> str:
    request = Request(url, headers={"User-Agent": "vexy-mkdocs-page-import"})
    opener = build_opener(_HTTPRedirects)
    attempt = 1
    while True:
        try:
            with opener.open(request, timeout=timeout) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                html: str = response.read().decode(charset)
            if not html.strip():
                raise ValueError("empty HTML")
            return html
        except (OSError, HTTPException, ValueError, LookupError) as exc:
            if isinstance(exc, HTTPError):
                exc.close()
                if 400 <= exc.code < 500 or urlsplit(exc.url).scheme not in HTTP_SCHEMES:
                    raise PluginError(f"failed to fetch {url}: {exc}") from exc
            if attempt == ATTEMPTS:
                raise PluginError(f"failed to fetch {url} after {attempt} attempts: {exc}") from exc
            time.sleep(0.1 * attempt)
            attempt += 1


def _store(path: Path, html: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=path.parent) as temp:
        staged = Path(temp) / path.name
        staged.write_bytes(html.encode("utf-8"))
        staged.replace(path)


def _read_cache(path: Path) -> str | None:
    try:
        if not path.is_file():
            return None
        html = path.read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    return html if html.strip() else None


def fetch(url: str, config_dir: Path, options: PageImportConfig) -> str:
    """Read one URL according to the offline, refresh and failure-fallback rules."""
    parts = urlsplit(url)
    if parts.scheme not in HTTP_SCHEMES or not parts.hostname:
        raise PluginError(f"expected an HTTP or HTTPS URL, got {url!r}")
    key = hashlib.sha256(url.encode("utf-8")).hexdigest()
    path = config_dir / options.cache_dir / f"{key}.html"
    if options.offline or not options.refresh:
        if (cached := _read_cache(path)) is not None:
            return cached
        if options.offline:
            raise PluginError(f"offline cache miss for {url}")
    try:
        html = _download(url, options.timeout)
    except PluginError as exc:
        if (cached := _read_cache(path)) is None:
            raise
        log.warning("%s; using cached copy", exc)
        return cached
    _store(path, html)
    return html
