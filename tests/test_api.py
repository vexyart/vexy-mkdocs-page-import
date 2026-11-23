# this_file: tests/test_api.py
"""Exercise the standalone toolkit helpers and their on-disk contract."""

import hashlib
import subprocess
import sys
from pathlib import Path
from types import MappingProxyType

import pytest
from conftest import HTML, Origin, build_page

import vexy_mkdocs_page_import as api


def test_api_when_imported_without_a_builder_then_helpers_are_available() -> None:
    subprocess.run(
        [
            sys.executable,
            "-S",
            "-c",
            "from vexy_mkdocs_page_import import cache_path, read_cached, refresh_cache, "
            "import_keys\nimport sys\nassert 'mkdocs' not in sys.modules",
        ],
        cwd=Path(api.__file__).resolve().parent.parent,
        check=True,
    )


@pytest.mark.parametrize("key", ["import-url", "webflow-import-url", "copy-file"])
def test_import_keys_when_mapping_has_one_key_then_returns_key_and_value(key: str) -> None:
    meta = MappingProxyType({"title": "Guide", key: "my source"})
    assert api.import_keys(meta) == (key, "my source")


def test_import_keys_when_there_is_no_import_then_returns_none() -> None:
    assert api.import_keys({"title": "Guide"}) is None


@pytest.mark.parametrize(
    "meta", [{"import-url": "a", "copy-file": "b"}, {"copy-file": " "}, {"import-url": 5}]
)
def test_import_keys_when_conflicting_or_invalid_then_raises_value_error(
    meta: dict[str, object],
) -> None:
    with pytest.raises(ValueError):
        api.import_keys(meta)


def test_read_cached_when_plugin_writes_entry_then_returns_original_html(
    tmp_path: Path, origin: Origin
) -> None:
    directory = tmp_path / "cache"
    url = origin.url + "?version=1"
    path = api.cache_path(directory, url)
    assert path == directory / (hashlib.sha256(url.encode()).hexdigest() + ".html")
    assert api.read_cached(directory, url) is None
    assert not directory.exists()
    origin.html = HTML + "\r\n"
    build_page(tmp_path, {"webflow-import-url": url}, cache_dir="cache")
    assert api.read_cached(directory, url) == origin.html
    path.write_bytes(b"\xff")
    assert api.read_cached(directory, url) is None


def test_refresh_cache_when_fetched_again_then_atomically_replaces_html(
    tmp_path: Path, origin: Origin
) -> None:
    directory = tmp_path / "cache"
    path = api.cache_path(directory, origin.url)
    assert api.refresh_cache(origin.url, directory) == HTML
    assert path.read_bytes() == HTML.encode()
    previous = tmp_path / "previous.html"
    previous.hardlink_to(path)
    origin.html = "<p>Édition 2</p>\r\n"
    assert api.refresh_cache(origin.url, directory) == origin.html
    assert path.read_bytes() == origin.html.encode()
    assert previous.read_bytes() == HTML.encode()
    assert list(directory.iterdir()) == [path]


def test_refresh_cache_when_fetch_fails_then_keeps_existing_file(
    tmp_path: Path, origin: Origin
) -> None:
    path = api.cache_path(tmp_path, origin.url)
    path.write_bytes(b"previous")
    with pytest.raises(OSError, match="max_bytes"):
        api.refresh_cache(origin.url, tmp_path, retries=0, max_bytes=1)
    assert path.read_bytes() == b"previous"
    assert list(tmp_path.iterdir()) == [path]


def test_plugin_when_imported_and_built_offline_then_aiohttp_stays_unloaded(
    tmp_path: Path, origin: Origin
) -> None:
    cache = tmp_path / "cache"
    cache.mkdir()
    api.cache_path(cache, origin.url).write_bytes(HTML.encode())
    subprocess.run(
        [
            sys.executable,
            "-c",
            """\
import sys
from pathlib import Path
import vexy_mkdocs_page_import, vexy_mkdocs_page_import.plugin
assert 'aiohttp' not in sys.modules
from conftest import HTML, build_page
page = build_page(Path(sys.argv[1]), {'import-url': sys.argv[2]}, offline=True, cache_dir='cache')
assert page == HTML
assert 'aiohttp' not in sys.modules
""",
            str(tmp_path),
            origin.url,
        ],
        cwd=Path(__file__).parent,
        check=True,
    )
    assert not origin.agents
