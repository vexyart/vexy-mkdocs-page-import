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
            "from vexy_mkdocs_page_import import cache_path, "
            "read_cached, import_keys; import sys; assert 'mkdocs' not in sys.modules",
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
