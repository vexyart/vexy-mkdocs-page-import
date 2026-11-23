# this_file: tests/test_fetch.py
"""Check fetch decisions against the origin request count and cache contents."""

from pathlib import Path

import pytest
from conftest import HTML, Origin, build_page
from mkdocs.exceptions import PluginError


@pytest.mark.parametrize("cached", [False, True])
def test_fetch_when_origin_returns_404_then_uses_one_attempt(
    tmp_path: Path, origin: Origin, cached: bool
) -> None:
    meta = {"import-url": origin.url}
    if cached:
        build_page(tmp_path, meta)
        origin.agents.clear()
    origin.error_code = 404
    origin.failures = 1
    if cached:
        assert build_page(tmp_path, meta) == HTML
    else:
        with pytest.raises(PluginError, match="404"):
            build_page(tmp_path, meta)
    assert len(origin.agents) == 1


@pytest.mark.parametrize("url", ["file:///unused.html", "ftp://127.0.0.1/unused.html"])
def test_fetch_when_import_scheme_unsupported_then_rejects_url(tmp_path: Path, url: str) -> None:
    with pytest.raises(PluginError, match="HTTP or HTTPS"):
        build_page(tmp_path, {"import-url": url})


@pytest.mark.parametrize("url", ["file:///unused.html", "ftp://127.0.0.1/unused.html"])
def test_fetch_when_redirect_scheme_unsupported_then_refuses_redirect(
    tmp_path: Path, origin: Origin, url: str
) -> None:
    origin.redirect = url
    with pytest.raises(PluginError, match=r"[Rr]edirect"):
        build_page(tmp_path, {"import-url": origin.url})
    assert len(origin.agents) == 1


def test_fetch_when_redirect_is_relative_then_follows_http_redirect(
    tmp_path: Path, origin: Origin
) -> None:
    origin.redirect = "/article"
    assert build_page(tmp_path, {"import-url": origin.url}) == HTML
    assert origin.agents == ["vexy-mkdocs-page-import"] * 2


@pytest.mark.parametrize("defect", ["encoding", "blank", "unreadable"])
def test_fetch_when_cache_unusable_then_misses_offline_and_refetches_online(
    tmp_path: Path, origin: Origin, monkeypatch: pytest.MonkeyPatch, defect: str
) -> None:
    meta = {"import-url": origin.url}
    build_page(tmp_path, meta)
    (cache,) = (tmp_path / ".cache/page-import").iterdir()
    with monkeypatch.context() as patch:
        if defect == "unreadable":
            read_bytes = Path.read_bytes

            def read(path: Path) -> bytes:
                if path == cache:
                    raise PermissionError("unreadable cache entry")
                return read_bytes(path)

            patch.setattr(Path, "read_bytes", read)
        else:
            cache.write_bytes(b"\xff" if defect == "encoding" else b" \n")
        with pytest.raises(PluginError, match="offline cache miss"):
            build_page(tmp_path, meta, offline=True)
        assert len(origin.agents) == 1
        origin.error_code = 404
        origin.failures = 1
        with pytest.raises(PluginError, match="404"):
            build_page(tmp_path, meta)
        origin.html = "<p>New copy</p>"
        assert build_page(tmp_path, meta, refresh=False) == origin.html
    assert len(origin.agents) == 3
    assert cache.read_text(encoding="utf-8") == origin.html
