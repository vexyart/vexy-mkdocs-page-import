# this_file: tests/test_fetch.py
"""Check fetch decisions against the origin request count and cache contents."""

import logging
import subprocess
import sys
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


def test_fetch_when_404_serves_cache_then_strict_cli_succeeds(
    tmp_path: Path, origin: Origin
) -> None:
    url = origin.url + "?token=hidden-query#hidden-fragment"
    build_page(tmp_path, {"import-url": url})
    origin.error_code = 404
    origin.failures = 1
    build = subprocess.run(
        [sys.executable, "-m", "mkdocs", "build", "--strict"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    assert "404" in build.stderr and "serving cached copy" in build.stderr
    assert "hidden-query" not in build.stderr and "hidden-fragment" not in build.stderr
    assert (tmp_path / "site/imported/index.html").read_text(encoding="utf-8") == HTML
    assert len(origin.agents) == 2


@pytest.mark.parametrize("mode", ["miss", "offline", "keep"])
def test_fetch_when_cache_missing_then_redacts_urls_in_logs_and_errors(
    tmp_path: Path, origin: Origin, caplog: pytest.LogCaptureFixture, mode: str
) -> None:
    url = origin.url + "?token=hidden-query#hidden-fragment"
    origin.error_code = 404
    origin.failures = 1
    meta = {"import-url": url}
    with caplog.at_level(logging.INFO):
        if mode == "keep":
            build_page(tmp_path, meta, offline=True, on_offline_miss="keep")
        else:
            with pytest.raises(PluginError) as exc:
                build_page(tmp_path, meta, offline=mode == "offline")
            assert "hidden-" not in str(exc.value)
    assert "hidden-" not in caplog.text
    if mode == "miss":
        assert any(
            record.levelno == logging.WARNING and "no cached copy" in record.getMessage()
            for record in caplog.records
        )


def test_fetch_when_body_exceeds_plugin_cap_then_preserves_cache(
    tmp_path: Path, origin: Origin
) -> None:
    meta = {"import-url": origin.url}
    assert build_page(tmp_path, meta, max_bytes=len(HTML.encode())) == HTML
    origin.html += "!"
    assert build_page(tmp_path, meta, max_bytes=len(HTML.encode())) == HTML
    assert len(origin.agents) == 2
