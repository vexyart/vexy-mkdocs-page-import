# this_file: tests/test_cloudinary_parity.py
"""Compare complete UTF-8 output against the installed FontLab toolkit source checkout."""

import importlib
import sys
from pathlib import Path
from types import ModuleType

import pytest
from conftest import Origin, build_page

from vexy_mkdocs_page_import.cloudinary import process_html_cloudinary

TOOLKIT_SRC = Path.home() / "Developer/vcs3/github.fontlab/fontlab-www-toolkit/src"
CDN = "https://cdn.prod.website-files.com/67c7070e70765599c7796390"
BASE = {
    "cl_cloud": "fontlab",
    "cl_map": {CDN: "vw"},
    "cl_trans": "c_limit,w_auto/f_auto,q_auto,dpr_auto/",
}


@pytest.fixture
def reference(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    builder = TOOLKIT_SRC / "fontlab_www_toolkit/builder.py"
    if not builder.is_file():
        pytest.skip(f"FontLab toolkit reference checkout is absent: {builder}")
    with monkeypatch.context() as patch:
        patch.setattr(sys, "dont_write_bytecode", True)
        patch.syspath_prepend(str(TOOLKIT_SRC))
        module = importlib.import_module("fontlab_www_toolkit.builder")
    assert Path(module.__file__).resolve() == builder.resolve()
    return module


@pytest.mark.parametrize(
    ("head", "markup", "options"),
    [
        pytest.param(
            "",
            f"<img class='hero cld-responsive' data-caption='Café' src='{CDN}/photo.jpg?size=2' "
            f"srcset='{CDN}/photo.jpg 2x'><img data-cld-responsive='false' src='{CDN}/still.png'>",
            {
                "cl_responsive": {
                    "cl_trans_thumb": "c_limit,w_128/f_auto,q_1/",
                    "cl_core_js": "https://unpkg.com/cloudinary-core@latest",
                    "methodology": "modern",
                    "lazyload": "observer",
                    "placeholder": "blur",
                }
            },
            id="production-modern-observer",
        ),
        pytest.param(
            '<link rel="stylesheet" href="https://fonts.googleapis.com/css2'
            '?family=Alegreya&amp;family=Outfit&amp;display=swap">',
            f'<img src="{CDN}/logo.SVG?x=1#icon"><img src="{CDN}/raster.jpg">'
            f'<div style="background:url({CDN}/vector.svg)"></div>',
            {
                "cl_trans_svg": "f_svg",
                "cl_responsive": {
                    "lazyload": "native",
                    "placeholder": False,
                    "accessibility": "monochrome",
                },
            },
            id="modern-native-svg-blank",
        ),
        pytest.param(
            "",
            f'<img src="{CDN}/old.webp"><img data-cld-responsive=" FALSE " src="{CDN}/tiny.gif">',
            {
                "cl_trans_static": "q_62",
                "cl_responsive": {
                    "methodology": "legacy",
                    "lazyload": True,
                    "cl_core_js": "/assets/cloudinary.js",
                    "cl_trans_thumb": "w_74",
                },
            },
            id="legacy-custom-library-thumbnail",
        ),
        pytest.param(
            "",
            f"<style>.pic{{background:url('{CDN}/bg.png')}}</style>"
            f'<video poster="https://res.cloudinary.com/foo/image/fetch/{CDN}/poster.png"></video>'
            f'<a href="{CDN}/manual.pdf">manual</a><img src="{CDN}/cover.jpg">',
            {"accessibility": "darkmode", "lazyload": "native"},
            id="static-media-and-exclusions",
        ),
        pytest.param(
            "",
            f'<img src="{CDN}/icon.jpg"><script type="application/json">{{}}</script>',
            {
                "cl_responsive": {
                    "cl_custom_js": "<script>one()</script><script>two()</script>",
                    "placeholder": "pixelate",
                }
            },
            id="custom-script-tags",
        ),
        pytest.param(
            "",
            f'<img src="{CDN}/x.avif"><script id="fontlab-toolkit-config" type="application/json">'
            '{"cloudinary":{"cl_cloud":"override"}}</script>',
            {"cl_responsive": {"cl_custom_js": "initImages()", "accessibility": "colorblind"}},
            id="custom-script-with-page-override",
        ),
    ],
)
def test_build_when_cloudinary_config_matches_toolkit_then_bytes_match(
    reference: ModuleType,
    tmp_path: Path,
    origin: Origin,
    *,
    head: str,
    markup: str,
    options: dict[str, object],
) -> None:
    html = f"<!doctype html><html><head><title>É</title>{head}</head><body>{markup}</body></html>"
    cloudinary = {**BASE, **options}
    builder = reference.SiteBuilder(reference.BuildPaths.from_root(tmp_path))
    expected = builder.process_html_cloudinary(html, cloudinary)
    assert process_html_cloudinary(html, cloudinary).encode("utf-8") == expected.encode("utf-8")

    builder.config = {"cloudinary": cloudinary}
    origin.html = html
    build_page(tmp_path, {"webflow-import-url": origin.url}, webflow=builder.config)
    published = (tmp_path / "site/imported/index.html").read_bytes()
    assert published == builder.process_page_html(html).encode("utf-8")
