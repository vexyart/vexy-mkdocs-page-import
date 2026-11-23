# this_file: tests/test_cloudinary.py
"""Cloudinary behaviour from fontlab-www-toolkit's test_cloudinary.py."""

import json
from pathlib import Path

import pytest
from bs4 import BeautifulSoup
from conftest import Origin, build_page

from vexy_mkdocs_page_import.cloudinary import process_html_cloudinary

CDN = "https://cdn.prod.website-files.com/67c7070e70765599c7796390"
UPLOAD = "https://res.cloudinary.com/testcloud/image/upload/"
TRANS = "c_limit,w_auto/f_auto,q_auto/"
IMAGE = f'<html><body><img src="{CDN}/photo.jpg"></body></html>'


def responsive(html: str = IMAGE, **settings: object) -> str:
    config = {
        "cl_cloud": "testcloud",
        "cl_map": {CDN: "vw"},
        "cl_trans": TRANS,
        "cl_responsive": {"methodology": "modern", **settings},
    }
    return process_html_cloudinary(html, config)


def test_build_when_inline_cloudinary_config_then_uses_page_settings(
    tmp_path: Path, origin: Origin
) -> None:
    config = {"cl_map": {CDN: "vw"}, "cl_cloud": "custom_cloud"}
    inline = {**config, "cl_responsive": {"methodology": "legacy"}}
    origin.html = (
        '<html><head><script id="fontlab-toolkit-config" type="application/json">'
        + json.dumps({"cloudinary": inline})
        + f'</script></head><body><img src="{CDN}/photo.jpg"></body></html>'
    )
    html = build_page(tmp_path, {"webflow-import-url": origin.url})
    assert "cloudinary-core" in html
    assert "cloudinary.Cloudinary.new({cloud_name: 'custom_cloud'});" in html
    assert "https://res.cloudinary.com/custom_cloud/image/upload/" in html


def test_build_when_flat_nested_and_inline_settings_overlap_then_more_specific_wins(
    tmp_path: Path, origin: Origin
) -> None:
    origin.html = (
        '<head><script id="fontlab-toolkit-config" type="application/json">'
        '{"cloudinary":{"cl_trans":"q_37"}}</script></head>'
        f'<body><img src="{CDN}/photo.jpg"></body>'
    )
    webflow = {
        "cl_cloud": "flat",
        "cl_map": {CDN: "vw"},
        "cl_trans": "w_320",
        "cloudinary": {"cl_cloud": "nested", "cl_trans": "w_160"},
    }
    html = build_page(tmp_path, {"webflow-import-url": origin.url}, webflow=webflow)
    assert 'src="https://res.cloudinary.com/nested/image/upload/q_37/vw/photo.jpg"' in html


def test_cloudinary_when_mapping_images_and_css_then_builds_responsive_urls() -> None:
    html = (
        f'<img src="{CDN}/photo.jpg" srcset="{CDN}/photo.jpg 2x">'
        """<div style="background-image: url('https://i.vexy.art/bg.png');"></div>"""
        '<a href="https://i.fontlab.com/doc.pdf">PDF</a>'
    )
    config = {
        "cl_cloud": "testcloud",
        "cl_map": {CDN: "vw", "https://i.vexy.art": "v", "https://i.fontlab.com": "i"},
        "cl_trans": TRANS,
        "cl_responsive": {"methodology": "modern", "cl_trans_thumb": "c_limit,w_100/f_auto/"},
    }
    out = process_html_cloudinary(html, config)
    img = BeautifulSoup(out, "html.parser").img
    assert img["class"] == ["cld-responsive"]
    assert img["data-src"] == UPLOAD + TRANS + "vw/photo.jpg"
    assert img["src"] == UPLOAD + "c_limit,w_100/f_auto/vw/photo.jpg"
    assert not img.has_attr("srcset")
    assert f"background-image: url('{UPLOAD}{TRANS}v/bg.png')" in out
    assert 'href="https://i.fontlab.com/doc.pdf"' in out


def test_cloudinary_when_svg_or_opted_out_then_uses_static_transform() -> None:
    out = responsive(
        f'<img id="svg" src="{CDN}/x.svg"><img id="png" src="{CDN}/y.png">'
        f'<img id="out" data-cld-responsive="false" src="{CDN}/logo.png">'
        f'<div style="background-image:url({CDN}/bg.svg)"></div>',
        placeholder="blur",
    )
    soup = BeautifulSoup(out, "html.parser")
    for element, transform in [
        ("svg", "f_svg,q_auto/vw/x.svg"),
        ("out", "f_auto,q_auto/vw/logo.png"),
    ]:
        img = soup.find(id=element)
        assert img["src"] == UPLOAD + transform
        assert not img.has_attr("class") and not img.has_attr("data-src")
    png = soup.find(id="png")
    assert "cld-responsive" in png["class"] and "w_auto" in png["data-src"]
    assert f"url({UPLOAD}f_svg,q_auto/vw/bg.svg)" in out


def test_cloudinary_when_legacy_then_loads_configured_library_and_initializes() -> None:
    url = "https://custom.cdn/cloudinary-core.js"
    out = responsive(methodology="legacy", cl_core_js=url)
    assert f'<script src="{url}" type="text/javascript"></script>' in out
    assert "var cl = cloudinary.Cloudinary.new({cloud_name: 'testcloud'});" in out
    assert "cl.responsive();" in out


@pytest.mark.parametrize("lazyload", [True, "observer", "native", False])
def test_cloudinary_when_modern_then_lazyload_and_observers_follow_setting(
    lazyload: bool | str,
) -> None:
    out = responsive(lazyload=lazyload)
    assert ('loading="lazy"' in out) == bool(lazyload)
    assert ("IntersectionObserver" in out) == (lazyload in (True, "observer"))
    assert "ResizeObserver" in out and "cld-responsive" in out and "cloudinary-core" not in out
    assert "blur(4px)" in out and "style.opacity" not in out and "opacity 0.4s" not in out


@pytest.mark.parametrize(
    ("placeholder", "transform"),
    [
        ("blur", "e_blur:2000,f_auto,q_auto:low"),
        ("pixelate", "e_pixelate:100,f_auto,q_auto:low"),
        ("vectorize", "e_vectorize,f_auto,q_auto:low"),
        ("predominant", "c_fill,w_1,h_1/f_auto,q_auto:low"),
        ("predominant-color", "c_fill,w_1,h_1/f_auto,q_auto:low"),
        ("custom-trans-string", "custom-trans-string"),
    ],
)
def test_cloudinary_when_placeholder_selected_then_sets_preview_url(
    placeholder: str, transform: str
) -> None:
    out = responsive(placeholder=placeholder)
    assert BeautifulSoup(out, "html.parser").img["src"] == f"{UPLOAD}{transform}/vw/photo.jpg"


def test_cloudinary_when_placeholder_false_then_uses_blank_gif() -> None:
    blank = "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"
    assert BeautifulSoup(responsive(placeholder=False), "html.parser").img["src"] == blank


@pytest.mark.parametrize(
    ("accessibility", "transform"),
    [
        ("colorblind", "e_assist_colorblind"),
        ("monochrome", "e_grayscale"),
        ("darkmode", "e_brightness_hsb:-30"),
        ("brightmode", "e_brightness_hsb:30"),
        ("custom-acc-effect", "custom-acc-effect"),
    ],
)
def test_cloudinary_when_accessibility_set_then_applies_to_both_image_urls(
    accessibility: str, transform: str
) -> None:
    out = responsive(placeholder="blur", accessibility=accessibility)
    img = BeautifulSoup(out, "html.parser").img
    assert img["data-src"] == f"{UPLOAD}{TRANS}{transform}/vw/photo.jpg"
    assert img["src"] == f"{UPLOAD}e_blur:2000,f_auto,q_auto:low/{transform}/vw/photo.jpg"


def test_cloudinary_when_static_mapping_then_excludes_nonmedia_and_nested_fetch_urls() -> None:
    nested = f"https://res.cloudinary.com/testcloud/image/fetch/q_60/f_auto/{CDN}/poster.png"
    html = (
        f'<link rel="stylesheet" href="{CDN}/site.css"><script src="{CDN}/site.js"></script>'
        f'<link rel="manifest" href="{CDN}/manifest.json"><style>'
        f"@font-face{{src:url('{CDN}/test.woff2')}} .bg{{background:url('{CDN}/bg.png')}}"
        f'</style><a href="{CDN}/doc.pdf">PDF</a><a href="{CDN}/archive.zip">ZIP</a>'
        f'<video poster="{nested}"></video><img src="{CDN}/photo.jpg">'
    )
    config = {"cl_map": {CDN: "vw"}, "cl_cloud": "testcloud", "cl_trans": TRANS}
    out = process_html_cloudinary(html, config)
    for path in ["site.css", "site.js", "manifest.json", "test.woff2", "doc.pdf", "archive.zip"]:
        assert f"{CDN}/{path}" in out
    assert f'poster="{nested}"' in out
    assert f"url('{UPLOAD}{TRANS}vw/bg.png')" in out
    assert f'src="{UPLOAD}{TRANS}vw/photo.jpg"' in out
