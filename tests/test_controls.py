# this_file: tests/test_controls.py
"""Build the same Markdown page with the import controls enabled and disabled."""

import logging
from pathlib import Path
from unittest.mock import patch

import pytest
from conftest import HTML, Origin, build_page
from mkdocs.exceptions import Abort, PluginError


def test_build_when_disabled_then_ignores_imports_and_invalid_settings(
    tmp_path: Path, origin: Origin
) -> None:
    normal = build_page(tmp_path, {"title": "Guide"})
    with patch("vexy_mkdocs_page_import.fetch.read_cached") as read_cache:
        for source in [
            {"import-url": origin.url},
            {"copy-file": "missing.html", "webflow-import-url": origin.url},
        ]:
            assert (
                build_page(
                    tmp_path, {"title": "Guide", **source}, enabled=False, timeout=0, refresh=False
                )
                == normal
            )
        read_cache.assert_not_called()
    assert not origin.agents
    assert not (tmp_path / ".cache").exists()


@pytest.mark.parametrize("key", ["import-url", "webflow-import-url"])
def test_build_when_offline_keep_misses_then_logs_page_and_keeps_rendered_markdown(
    tmp_path: Path, origin: Origin, caplog: pytest.LogCaptureFixture, key: str
) -> None:
    normal = build_page(tmp_path, {"title": "Guide"})
    with caplog.at_level(logging.INFO):
        output = build_page(
            tmp_path, {"title": "Guide", key: origin.url}, offline=True, on_offline_miss="keep"
        )
    assert output == normal
    assert any(
        r.levelno == logging.INFO and "imported.md" in r.getMessage() for r in caplog.records
    )
    assert not origin.agents


def test_build_when_offline_keep_hits_then_imports_cached_html(
    tmp_path: Path, origin: Origin
) -> None:
    meta = {"import-url": origin.url}
    build_page(tmp_path, meta)
    assert build_page(tmp_path, meta, offline=True, on_offline_miss="keep") == HTML
    assert len(origin.agents) == 1


def test_build_when_keep_and_copy_file_missing_then_raises_error(tmp_path: Path) -> None:
    with pytest.raises(PluginError, match=r"missing\.html"):
        build_page(tmp_path, {"copy-file": "missing.html"}, offline=True, on_offline_miss="keep")


def test_build_when_keep_and_online_fetch_fails_then_raises_error(
    tmp_path: Path, origin: Origin
) -> None:
    origin.error_code = 404
    origin.failures = 1
    with pytest.raises(PluginError, match="404"):
        build_page(tmp_path, {"import-url": origin.url}, on_offline_miss="keep")


def test_build_when_offline_miss_policy_unknown_then_rejects_config(tmp_path: Path) -> None:
    with pytest.raises(Abort):
        build_page(tmp_path, {"title": "Guide"}, on_offline_miss="ignore")
