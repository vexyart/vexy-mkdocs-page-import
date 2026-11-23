# this_file: src/vexy_mkdocs_page_import/webflow.py
"""Apply the FontLab toolkit's Webflow export transformations."""

import json
import re
from html.parser import HTMLParser
from typing import Any

from bs4 import BeautifulSoup, Doctype
from mkdocs.plugins import get_plugin_logger

from .cloudinary import apply_cloudinary
from .config import WebflowConfig

log = get_plugin_logger(__name__)
_MISSING_HEAD = "%s: missing </head>, skipping inject_head"
_EXECUTABLE_TYPES = {
    "",
    "text/javascript",
    "application/javascript",
    "text/ecmascript",
    "application/ecmascript",
    "module",
}


class _HeadEnd(HTMLParser):
    """Locate a real end tag without serializing the page."""

    position: tuple[int, int] | None = None
    handle_startendtag = HTMLParser.handle_starttag  # A self-closing tag has no end-tag token.

    def handle_endtag(self, tag: str) -> None:
        if tag == "head" and self.position is None:
            self.position = self.getpos()

    @classmethod
    def locate(cls, html: str) -> tuple[int, int] | None:
        parser = cls()
        parser.feed(html)
        parser.close()
        return parser.position


def insert_head(html: str, snippet: str, *, page_name: str = "Imported HTML") -> str:
    """Insert a literal fragment before the first closing head, at most once."""
    if not snippet or snippet in html:
        return html
    position = _HeadEnd.locate(html)
    if position is None:
        log.warning(_MISSING_HEAD, page_name)
        return html
    line, column = position
    offset = 0
    for _ in range(line - 1):
        offset = html.index("\n", offset) + 1
    offset += column
    return html[:offset] + snippet + html[offset:]


def _cloudinary_config(soup: BeautifulSoup, options: WebflowConfig) -> dict[str, Any]:
    """Merge site settings with this export's Cloudinary overrides."""
    config = options.cloudinary.copy()
    script = soup.find("script", id="page-import-config", type="application/json")
    if script and script.string:
        try:
            page = json.loads(script.string)
        except json.JSONDecodeError:
            return config
        if isinstance(page, dict) and isinstance(page.get("cloudinary"), dict):
            config.update(page["cloudinary"])
    return config


def _split_fonts(soup: BeautifulSoup) -> bool:
    changed = False
    for link in soup.select("link[href]"):
        base, _, query = str(link["href"]).partition("?")
        if not re.fullmatch(r"(?:https?:)?//fonts\.googleapis\.com/css2", base):
            continue
        params = query.split("&")
        families = [p for p in params if p.startswith("family=")]
        if len(families) < 2:
            continue
        extras = [p for p in params if p and not p.startswith("family=")]
        for family in families:
            href = base + "?" + "&".join([family, *extras])
            link.insert_before(soup.new_tag("link", rel="stylesheet", href=href))
        link.extract()
        changed = True
    return changed


def _hide_badge(
    soup: BeautifulSoup, css: str, html: str, has_head_end: bool, page_name: str
) -> bool:
    badges = soup.select("a.w-webflow-badge")
    for badge in badges:
        badge.decompose()
    if not css:
        return bool(badges)
    style = css if css.lstrip().lower().startswith("<style") else f"<style>{css}</style>"
    if style in html:
        return bool(badges)
    fragment = BeautifulSoup(style, "html.parser")
    if not has_head_end:
        log.warning("%s: no closing </head> tag for the badge style", page_name)
    head = soup.head
    if head is None:
        head = soup.new_tag("head")
        parent = soup.html or soup
        doctype = next((node for node in parent.contents if isinstance(node, Doctype)), None)
        if doctype is None:
            parent.insert(0, head)
        else:
            doctype.insert_after(head)
    head.append(fragment)
    return True


def _exempt_scripts(soup: BeautifulSoup) -> bool:
    changed = False
    for script in soup.select("script"):
        if (
            not script.has_attr("data-cfasync")
            and str(script.get("type", "")).strip().lower() in _EXECUTABLE_TYPES
        ):
            script["data-cfasync"] = "false"
            changed = True
    return changed


def process_webflow(
    html: str, options: WebflowConfig, inject_head: str = "", *, page_name: str = "Imported HTML"
) -> str:
    """Process Webflow HTML before the plugin returns it to the site builder."""
    soup = BeautifulSoup(html, "html.parser")
    cloudinary = _cloudinary_config(soup, options)
    # BeautifulSoup may synthesize a closing head tag in a malformed export.
    has_head_end = _HeadEnd.locate(html) is not None
    badge_changed = options.strip_badge and _hide_badge(
        soup, options.badge_hide_css, html, has_head_end, page_name
    )
    fonts_changed = options.split_google_fonts and _split_fonts(soup)
    if cloudinary.get("cl_map"):
        # The toolkit reparses after a font split and before Rocket Loader. These
        # round trips affect whitespace, including the newline after a doctype.
        if fonts_changed:
            soup = BeautifulSoup(str(soup), "html.parser")
        apply_cloudinary(soup, cloudinary)
        out = str(soup)
        if options.rocket_loader_optout and "<script" in out:
            soup = BeautifulSoup(out, "html.parser")
    else:
        out = str(soup) if badge_changed or fonts_changed else html
    if options.rocket_loader_optout and _exempt_scripts(soup):
        out = str(soup)
    if not inject_head or inject_head in html:
        return out
    if not has_head_end:
        log.warning(_MISSING_HEAD, page_name)
        return out
    if options.rocket_loader_optout and "<script" in inject_head.lower():
        fragment = BeautifulSoup(inject_head, "html.parser")
        if _exempt_scripts(fragment):
            inject_head = str(fragment)
    return insert_head(out, inject_head, page_name=page_name)
