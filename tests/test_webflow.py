# this_file: tests/test_webflow.py
"""Webflow export cleanup and media mapping cases from the toolkit."""

import logging
from pathlib import Path

import pytest
from bs4 import BeautifulSoup
from conftest import Origin, build_page

from vexy_mkdocs_page_import.config import WebflowConfig
from vexy_mkdocs_page_import.webflow import insert_head, process_webflow

CDN = "https://cdn.prod.website-files.com/site"
UPLOAD = "https://res.cloudinary.com/testcloud/image/upload/"
TRANS = "c_limit,w_auto/f_auto,q_auto/"
HIDE = "<style>.w-webflow-badge{display:none !important;}</style>"
FONTS = "https://fonts.googleapis.com/css2?"


def test_insert_head_when_markup_contains_tag_literals_then_only_changes_real_head() -> None:
    before = (
        "<!DOCTYPE html>\r\n<head><!-- </head> -->\r\n"
        "<script>const close = '</head>';</script>\n"
        "<meta name='sample' content='</head>'>\r\n"
    )
    tail = "</HeAd  >\r\n<body>untouched</body>"
    snippet = "<meta charset='utf-8'>"
    assert insert_head(before + tail, snippet) == before + snippet + tail
    assert insert_head(before, snippet) == before


def test_build_when_cached_webflow_contains_tag_literals_then_injects_into_head(
    tmp_path: Path, origin: Origin
) -> None:
    origin.html = "<head><script>const close = '</head>';</script></head><body>ok</body>"
    meta = {"webflow-import-url": origin.url}
    build_page(tmp_path, meta)
    snippet = "<meta name='offline'>"
    output = build_page(tmp_path, meta, offline=True, inject_head=snippet)
    assert snippet + "</head>" in output
    assert "const close = '</head>';" in output
    assert len(origin.agents) == 1


def test_process_webflow_when_cloudinary_prefix_is_mapped_then_rewrites_each_media_use() -> None:
    prefix = "https://res.cloudinary.com/original/image/upload"
    src = prefix + "/portrait.jpg"
    html = (
        f'<img src="{src}"><video poster="{src}"></video><style>i{{background:url({src})}}</style>'
    )
    out = process(html, cl_map={prefix: "base"}, cl_trans="", cl_cloud="testcloud")
    assert out.count(UPLOAD + "base/portrait.jpg") == 3


def process(html: str, **settings: object) -> str:
    config = WebflowConfig()
    config.load_dict(settings)
    errors, warnings = config.validate()
    assert not errors and not warnings
    return process_webflow(html, config)


def map_media(html: str) -> str:
    return process(
        html,
        cl_map={CDN: "vw", "https://i.vexy.art": "v"},
        cl_cloud="testcloud",
        cl_trans=TRANS,
        strip_badge=False,
    )


def test_process_webflow_when_badges_present_then_removes_anchors_and_hides_once() -> None:
    html = (
        "<html><head></head><body><a class='keep w-webflow-badge'><img src='badge'></a>"
        "<a class=w-webflow-badge>second</a><i class=w-webflow-badge>keep</i></body></html>"
    )
    out = process(html)
    assert HIDE + "</head>" in out
    assert not BeautifulSoup(out, "html.parser").select("a.w-webflow-badge")
    assert ">keep</i>" in out
    assert process(out) == out


@pytest.mark.parametrize("css", [".w-webflow-badge{opacity:0}", "<style>x{}</style>"])
def test_process_webflow_when_head_missing_then_prepends_custom_style(css: str) -> None:
    expected = css if css.startswith("<style>") else f"<style>{css}</style>"
    assert process("<div>x</div>", badge_hide_css=css) == expected + "<div>x</div>"


def test_process_webflow_when_badge_removal_disabled_then_keeps_anchor() -> None:
    html = "<head></head><a class='w-webflow-badge'>keep</a>"
    assert process(html, strip_badge=False) == html


@pytest.mark.parametrize(
    "html", ["<body>fragment</body>", "<!DOCTYPE html><head><script>run()</script>"]
)
@pytest.mark.parametrize("key", ["import-url", "webflow-import-url"])
def test_build_when_missing_head_end_then_warns_with_page_and_skips_snippet(
    tmp_path: Path, origin: Origin, caplog: pytest.LogCaptureFixture, key: str, html: str
) -> None:
    origin.html = html
    output = build_page(tmp_path, {key: origin.url}, inject_head="<meta charset='UTF-8'>")
    assert "<meta" not in output
    warnings = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert any("imported.md" in w and "inject_head" in w and "</head>" in w for w in warnings)
    if key == "webflow-import-url":
        if "<head>" in html:
            assert output.startswith("<!DOCTYPE html>")
            assert str(BeautifulSoup(output, "html.parser").select_one("head > style")) == HIDE
        else:
            assert output.startswith(HIDE)
        assert any("imported.md" in w and "badge" in w and "</head>" in w for w in warnings)


def test_build_when_head_additions_present_then_headless_page_needs_no_warning(
    tmp_path: Path, origin: Origin, caplog: pytest.LogCaptureFixture
) -> None:
    snippet = "<meta charset='UTF-8'>"
    origin.html = HIDE + snippet
    build_page(tmp_path, {"webflow-import-url": origin.url}, inject_head=snippet)
    assert not any(r.levelno == logging.WARNING for r in caplog.records)


def test_process_webflow_when_css2_links_have_multiple_families_then_splits_each() -> None:
    html = (
        f'<link href="{FONTS}family=Crimson+Pro:wght@400&amp;family=A&amp;display=swap">'
        '<link href="/local.css">'
        f'<link href="{FONTS}family=B&amp;family=C">'
    )
    soup = BeautifulSoup(process(html), "html.parser")
    assert [link["href"] for link in soup.select("link")] == [
        FONTS + "family=Crimson+Pro:wght@400&display=swap",
        FONTS + "family=A&display=swap",
        "/local.css",
        FONTS + "family=B",
        FONTS + "family=C",
    ]


@pytest.mark.parametrize(
    ("query", "enabled"),
    [("family=A&amp;display=swap", True), ("family=A&amp;family=B", False)],
)
def test_process_webflow_when_font_splitting_unneeded_then_preserves_link(
    query: str, enabled: bool
) -> None:
    html = f"<link href='{FONTS}{query}'>"
    assert process(html, strip_badge=False, split_google_fonts=enabled) == html


def test_process_webflow_when_scripts_have_mixed_types_then_marks_only_unset_javascript() -> None:
    html = (
        "<script>inline()</script><script type=module src='/a.js'></script>"
        "<script type=' Text/JavaScript '></script><script type=application/javascript></script>"
        "<script type=text/ecmascript></script><script type=application/ecmascript></script>"
        "<script type='application/json'>{}</script><script type='application/ld+json'>{}</script>"
        "<script type=importmap>{}</script><script data-cfasync></script>"
        "<script data-cfasync=true></script><script data-cfasync=false></script>"
    )
    out = process(html)
    scripts = BeautifulSoup(out, "html.parser").select("script")
    assert [s.get("data-cfasync") for s in scripts] == ["false"] * 6 + [
        None,
        None,
        None,
        "",
        "true",
        "false",
    ]
    assert process(out) == out


def test_process_webflow_when_rocket_loader_option_disabled_then_keeps_scripts() -> None:
    html = "<script type='module' src='a.js'></script>"
    assert process(html, strip_badge=False, rocket_loader_optout=False) == html


def test_process_webflow_when_injecting_head_then_places_snippet_last_and_marks_scripts() -> None:
    config = WebflowConfig()
    snippet = "<script type='module'>run()</script>"
    html = process_webflow("<head></head><body></body>", config, snippet)
    assert HIDE + '<script data-cfasync="false" type="module">run()</script></head>' in html
    assert process_webflow(html, config, snippet) == html


def test_process_webflow_when_injecting_meta_then_preserves_literal_fragment() -> None:
    snippet = "<meta name='example' content='head'>"
    html = process_webflow("<head></head>", WebflowConfig(), snippet)
    assert html == "<head>" + HIDE + snippet + "</head>"
    assert process_webflow(html, WebflowConfig(), snippet) == html


def test_process_webflow_when_mapping_images_and_styles_then_rewrites_media() -> None:
    html = (
        f'<img src="{CDN}/photo.jpg" srcset="{CDN}/photo@2x.jpg 2x">'
        """<div style="background:url('https://i.vexy.art/bg.png')"></div>"""
        f"<style>.icon{{background:url({CDN}/icon.SVG?x=1#mark)}}</style>"
        f'<img src="{CDN}/logo.svg"><img data-cld-responsive=false src="{CDN}/optout.png">'
        f'<video src="{CDN}/intro.mp4"></video><audio src="{CDN}/song.ogg"></audio>'
    )
    out = map_media(html)
    assert "srcset=" not in out
    for path in ["vw/photo.jpg", "v/bg.png", "vw/intro.mp4", "vw/song.ogg"]:
        assert UPLOAD + TRANS + path in out
    for path in ["vw/icon.SVG?x=1#mark", "vw/logo.svg"]:
        assert UPLOAD + "f_svg,q_auto/" + path in out
    assert UPLOAD + "f_auto,q_auto/vw/optout.png" in out


def test_process_webflow_when_nonmedia_or_nested_fetch_then_preserves_urls() -> None:
    fetch = f"https://res.cloudinary.com/testcloud/image/fetch/q_60/f_auto/{CDN}/poster.png"
    html = (
        f'<link href="{CDN}/site.css"><script src="{CDN}/site.js"></script>'
        f'<link href="{CDN}/manifest.json"><style>@font-face{{src:url({CDN}/f.woff2)}}</style>'
        f'<a href="{CDN}/doc.pdf">PDF</a><a href="{CDN}/archive.zip">ZIP</a>'
        f'<video poster="{fetch}"></video><img src="{CDN}/poster.png">'
        f"<script>const poster = '{CDN}/script-only.png'</script>"
    )
    out = map_media(html)
    for path in ["site.css", "site.js", "manifest.json", "f.woff2", "doc.pdf", "archive.zip"]:
        assert f"{CDN}/{path}" in out
    assert f'poster="{fetch}"' in out
    assert f'src="{UPLOAD}{TRANS}vw/poster.png"' in out
    assert f"'{CDN}/script-only.png'" in out


def test_process_webflow_when_mapping_empty_then_preserves_media() -> None:
    html = f"<img src='{CDN}/x.jpg' srcset='{CDN}/y.jpg 2x'>"
    assert process(html, strip_badge=False) == html
