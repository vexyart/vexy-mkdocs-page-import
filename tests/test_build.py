# this_file: tests/test_build.py
"""Exercise the installed plugin through MkDocs' build command."""

import hashlib
import json
import logging
from io import BytesIO
from itertools import combinations
from pathlib import Path

import pytest
from bs4 import BeautifulSoup
from conftest import HTML, Origin, build_page
from mkdocs.commands.build import build
from mkdocs.config import load_config
from mkdocs.exceptions import PluginError


@pytest.mark.parametrize("key", ["import-url", "webflow-import-url", "copy-file"])
def test_build_when_page_imports_html_then_output_replaced_and_markdown_indexed(
    tmp_path: Path, origin: Origin, key: str
) -> None:
    (tmp_path / "export.html").write_text(HTML, encoding="utf-8")
    value = "export.html" if key == "copy-file" else origin.url
    output = build_page(tmp_path, {key: value})
    if key == "webflow-import-url":
        assert 'data-cfasync="false"' in output
        assert "Imported café" in output and "Searchable Markdown body" not in output
    else:
        assert output == HTML
    assert origin.agents == ([] if key == "copy-file" else ["vexy-mkdocs-page-import"])
    site = tmp_path / "site"
    home = BeautifulSoup((site / "index.html").read_text(), "html.parser")
    assert home.find("a", href="imported/")
    assert "Ordinary page." in home.get_text()
    index = json.loads((site / "search/search_index.json").read_text())["docs"]
    assert any(
        doc["location"].startswith("imported/") and "Searchable Markdown body." in doc["text"]
        for doc in index
    )


@pytest.mark.parametrize(
    "keys", list(combinations(["copy-file", "import-url", "webflow-import-url"], 2))
)
def test_build_when_keys_conflict_then_plugin_error_names_page(
    tmp_path: Path, origin: Origin, keys: tuple[str, str]
) -> None:
    with pytest.raises(PluginError, match=r"imported\.md"):
        build_page(tmp_path, dict.fromkeys(keys, origin.url))
    assert not origin.agents


def test_build_when_copy_file_missing_then_plugin_error_names_file(tmp_path: Path) -> None:
    with pytest.raises(PluginError, match=r"missing\.html"):
        build_page(tmp_path, {"copy-file": "missing.html"})


def test_build_when_config_has_no_file_then_resolves_copy_from_docs_parent(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "index.md").write_text("---\ncopy-file: export.html\n---\n# Guide\n", encoding="utf-8")
    (tmp_path / "export.html").write_text(HTML, encoding="utf-8")
    site = tmp_path / "site"
    theme = tmp_path / "theme"
    theme.mkdir()
    (theme / "main.html").write_text("{{ page.content }}", encoding="utf-8")
    config = load_config(
        config_file=BytesIO(b"site_name: Test\nplugins: [page-import]\n"),
        theme={"name": None, "custom_dir": str(theme)},
        docs_dir=str(docs),
        site_dir=str(site),
    )
    assert not config.config_file_path
    build(config)
    assert (site / "index.html").read_bytes() == HTML.encode()


@pytest.mark.parametrize(
    "source", ["absolute", "../export.html", "linked.html", "link/export.html"]
)
def test_build_when_copy_file_outside_root_then_plugin_error_names_page(
    tmp_path: Path, source: str
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    export = tmp_path / "export.html"
    export.write_text(HTML, encoding="utf-8")
    (project / "linked.html").symlink_to(export)
    (project / "link").symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(PluginError, match=r"imported\.md.*copy_root"):
        build_page(project, {"copy-file": str(export) if source == "absolute" else source})


def test_build_when_copy_file_is_absolute_even_inside_root_then_rejects_it(tmp_path: Path) -> None:
    export = tmp_path / "export.html"
    export.write_text(HTML, encoding="utf-8")
    with pytest.raises(PluginError, match="relative"):
        build_page(tmp_path, {"copy-file": str(export)})


@pytest.mark.parametrize("absolute_root", [False, True])
def test_build_when_export_inside_external_copy_root_then_imports_page(
    tmp_path: Path, absolute_root: bool
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    exports = tmp_path / "exports"
    exports.mkdir()
    (exports / "page.html").write_text(HTML, encoding="utf-8")
    copy_root = str(exports) if absolute_root else "../exports"
    assert build_page(project, {"copy-file": "../exports/page.html"}, copy_root=copy_root) == HTML
    (project / "private.html").write_text(HTML, encoding="utf-8")
    with pytest.raises(PluginError, match=r"imported\.md.*copy_root"):
        build_page(project, {"copy-file": "private.html"}, copy_root=copy_root)


def test_build_when_copy_root_is_file_then_plugin_error_names_page(tmp_path: Path) -> None:
    (tmp_path / "page.html").write_text(HTML, encoding="utf-8")
    with pytest.raises(PluginError, match=r"imported\.md.*copy_root"):
        build_page(tmp_path, {"copy-file": "page.html"}, copy_root="page.html")


@pytest.mark.parametrize("timeout", [0, -1, True])
def test_build_when_timeout_invalid_then_plugin_error_before_fetch(
    tmp_path: Path, origin: Origin, timeout: float
) -> None:
    with pytest.raises(PluginError, match="timeout"):
        build_page(tmp_path, {"import-url": origin.url}, timeout=timeout)
    assert not origin.agents


@pytest.mark.parametrize("max_bytes", [0, -1, True])
def test_build_when_max_bytes_invalid_then_plugin_error_before_fetch(
    tmp_path: Path, origin: Origin, max_bytes: int
) -> None:
    with pytest.raises(PluginError, match="max_bytes"):
        build_page(tmp_path, {"import-url": origin.url}, max_bytes=max_bytes)
    assert not origin.agents


@pytest.mark.parametrize("options", [{"refresh": False}, {"offline": True}])
def test_build_when_reusing_cache_then_origin_receives_no_request(
    tmp_path: Path, origin: Origin, options: dict[str, bool]
) -> None:
    url = origin.url
    build_page(tmp_path, {"import-url": url}, cache_dir="stored")
    (cached,) = (tmp_path / "stored").iterdir()
    assert cached.stem == hashlib.sha256(url.encode()).hexdigest()
    assert cached.read_text(encoding="utf-8") == HTML
    origin.html = "changed"
    assert build_page(tmp_path, {"import-url": url}, cache_dir="stored", **options) == HTML
    assert len(origin.agents) == 1


def test_build_when_offline_cache_missing_then_plugin_error_without_request(
    tmp_path: Path, origin: Origin
) -> None:
    with pytest.raises(PluginError):
        build_page(tmp_path, {"import-url": origin.url}, offline=True)
    assert not origin.agents


def test_build_when_refresh_enabled_then_cache_gets_new_source(
    tmp_path: Path, origin: Origin
) -> None:
    meta = {"import-url": origin.url}
    build_page(tmp_path, meta)
    origin.html = "<p>New source</p>"
    assert build_page(tmp_path, meta) == origin.html
    assert build_page(tmp_path, meta, offline=True) == origin.html
    assert len(origin.agents) == 2


@pytest.mark.parametrize("failures", [2, 3])
def test_build_when_origin_fails_then_retries_up_to_three_times(
    tmp_path: Path, origin: Origin, failures: int
) -> None:
    origin.failures = failures
    if failures == 3:
        with pytest.raises(PluginError):
            build_page(tmp_path, {"import-url": origin.url})
    else:
        assert build_page(tmp_path, {"import-url": origin.url}) == HTML
    assert len(origin.agents) == 3


def test_build_when_refresh_fails_then_logs_at_info_and_uses_cache(
    tmp_path: Path, origin: Origin, caplog: pytest.LogCaptureFixture
) -> None:
    meta = {"import-url": origin.url}
    build_page(tmp_path, meta)
    origin.failures = 3
    caplog.clear()
    with caplog.at_level(logging.INFO):
        assert build_page(tmp_path, meta) == HTML
    assert len(origin.agents) == 4
    assert any(
        r.levelno == logging.INFO and "cache" in r.getMessage().lower() for r in caplog.records
    )


@pytest.mark.parametrize("key", ["copy-file", "import-url", "webflow-import-url"])
@pytest.mark.parametrize("already_present", [True, False])
def test_build_when_inject_head_configured_then_snippet_appears_once(
    tmp_path: Path, origin: Origin, key: str, already_present: bool
) -> None:
    snippet = '<meta name="marker" content="one">'
    html = f"<html><head>{snippet if already_present else ''}</head><body></body></html>"
    origin.html = html
    (tmp_path / "export.html").write_text(html, encoding="utf-8")
    value = "export.html" if key == "copy-file" else origin.url
    output = build_page(tmp_path, {key: value}, inject_head=snippet)
    head = BeautifulSoup(output, "html.parser").head
    assert head is not None
    assert len(head.find_all("meta", attrs={"name": "marker", "content": "one"})) == 1
    if not already_present:
        assert snippet + "</head>" in output


def test_build_when_webflow_options_disabled_then_import_preserves_html(
    tmp_path: Path, origin: Origin
) -> None:
    origin.html = HTML.replace("</body>", '<a class="w-webflow-badge"></a></body>').replace(
        "</head>", '<link href="https://fonts.googleapis.com/css2?family=A&amp;family=B"></head>'
    )
    options = {"strip_badge": False, "split_google_fonts": False, "rocket_loader_optout": False}
    assert build_page(tmp_path, {"webflow-import-url": origin.url}, webflow=options) == origin.html


@pytest.mark.parametrize("key", ["import-url", "copy-file"])
def test_build_when_import_is_blank_then_plugin_error_names_page(
    tmp_path: Path, origin: Origin, key: str
) -> None:
    origin.html = " \n"
    (tmp_path / "empty.html").write_text(origin.html, encoding="utf-8")
    value = "empty.html" if key == "copy-file" else origin.url
    with pytest.raises(PluginError, match=r"imported\.md"):
        build_page(tmp_path, {key: value})


def test_build_when_cached_webflow_url_imported_as_plain_then_raw_html_returned(
    tmp_path: Path, origin: Origin
) -> None:
    assert 'data-cfasync="false"' in build_page(tmp_path, {"webflow-import-url": origin.url})
    assert build_page(tmp_path, {"import-url": origin.url}, offline=True) == HTML
    (cached,) = (tmp_path / ".cache/page-import").iterdir()
    assert cached.stem == hashlib.sha256(origin.url.encode()).hexdigest()
    assert len(origin.agents) == 1
