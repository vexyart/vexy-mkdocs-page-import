# this_file: tests/test_cloudinary_parity.py
"""Compare UTF-8 output with fontlab-www-toolkit goldens from commit 2b054e66579f."""

from pathlib import Path

import pytest
from conftest import Origin, build_page

from vexy_mkdocs_page_import.cloudinary import process_html_cloudinary

GOLDENS = Path(__file__).parent / "fixtures/cloudinary"
CDN = "https://cdn.prod.website-files.com/67c7070e70765599c7796390"
BASE = {
    "cl_cloud": "fontlab",
    "cl_map": {CDN: "vw"},
    "cl_trans": "c_limit,w_auto/f_auto,q_auto,dpr_auto/",
}


def golden(case: str, stage: str) -> bytes:
    expected = (GOLDENS / f"{case}.{stage}.html").read_bytes()
    # Keep the upstream bytes on disk, including the two spellings changed for 0.1.0.
    if case == "legacy-custom-library-thumbnail":
        return expected.replace(b"cloud_name: 'fontlab'", b'cloud_name: "fontlab"', 1)
    if case == "custom-script-with-page-override":
        return expected.replace(b'id="fontlab-toolkit-config"', b'id="page-import-config"', 1)
    return expected


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
            f'<img src="{CDN}/x.avif"><script id="page-import-config" type="application/json">'
            '{"cloudinary":{"cl_cloud":"override"}}</script>',
            {"cl_responsive": {"cl_custom_js": "initImages()", "accessibility": "colorblind"}},
            id="custom-script-with-page-override",
        ),
    ],
)
def test_build_when_cloudinary_config_matches_toolkit_then_bytes_match(
    request: pytest.FixtureRequest,
    tmp_path: Path,
    origin: Origin,
    *,
    head: str,
    markup: str,
    options: dict[str, object],
) -> None:
    html = f"<!doctype html><html><head><title>É</title>{head}</head><body>{markup}</body></html>"
    cloudinary = {**BASE, **options}
    case = request.node.callspec.id
    transformed = process_html_cloudinary(html, cloudinary).encode("utf-8")
    assert transformed == golden(case, "cloudinary")

    origin.html = html
    build_page(tmp_path, {"webflow-import-url": origin.url}, webflow={"cloudinary": cloudinary})
    published = (tmp_path / "site/imported/index.html").read_bytes()
    assert published == golden(case, "published")
