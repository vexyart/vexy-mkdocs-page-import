# this_file: src/vexy_mkdocs_page_import/cloudinary.py
"""Cloudinary URL mapping and responsive markup from fontlab-www-toolkit."""

import re
from typing import Any

from bs4 import BeautifulSoup, Tag

from .cloudinary_scripts import append_responsive_script

_MEDIA_EXTENSIONS = tuple(
    ".png .jpg .jpeg .webp .svg .gif .avif .ico .heic .heif .tiff .bmp "
    ".mp4 .webm .ogv .mov .mp3 .wav .ogg .aac .flac .m4a".split()
)
_DEFAULT_THUMB = "c_limit,w_128/f_auto,q_1/"
_BLANK_GIF = "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"
_PLACEHOLDERS = {
    "blur": "e_blur:2000,f_auto,q_auto:low",
    "pixelate": "e_pixelate:100,f_auto,q_auto:low",
    "vectorize": "e_vectorize,f_auto,q_auto:low",
    "predominant": "c_fill,w_1,h_1/f_auto,q_auto:low",
    "predominant-color": "c_fill,w_1,h_1/f_auto,q_auto:low",
}
_ACCESSIBILITY = {
    "colorblind": "e_assist_colorblind",
    "monochrome": "e_grayscale",
    "darkmode": "e_brightness_hsb:-30",
    "brightmode": "e_brightness_hsb:30",
}


def _path(url: str) -> str:
    return url.partition("?")[0].partition("#")[0].lower()


def _slash(value: str) -> str:
    return value if value.endswith("/") else value + "/"


def _lazyload(value: object, methodology: str) -> str:
    if value is True:
        return "observer" if methodology == "modern" else "native"
    return value.lower() if isinstance(value, str) else "false"


class _Delivery:
    """Resolve transforms once for all images, attributes and CSS on a page."""

    def __init__(self, config: dict[str, Any]) -> None:
        self.cloud: str = config.get("cl_cloud", "fontlab")
        self.mapping: dict[str, str] = config.get("cl_map", {})
        self.svg: str = config.get("cl_trans_svg", "f_svg,q_auto")
        self.static: str = config.get("cl_trans_static", "f_auto,q_auto")
        self.transform: str = config.get("cl_trans", "c_limit,w_auto/f_auto,q_auto,dpr_auto/")
        responsive = config.get("cl_responsive")
        self.enabled = bool(responsive)
        self.responsive = responsive if isinstance(responsive, dict) else {}
        self.methodology = self.responsive.get("methodology", "modern") if self.enabled else ""
        options = self.responsive if self.enabled else config
        self.lazyload = _lazyload(options.get("lazyload"), self.methodology)
        thumb = self.responsive.get("cl_trans_thumb") or _DEFAULT_THUMB
        placeholder = options.get("placeholder")
        self.blank = placeholder is False
        self.thumb = (
            _PLACEHOLDERS.get(placeholder.lower(), placeholder)
            if isinstance(placeholder, str)
            else thumb
        )
        effect = options.get("accessibility")
        if isinstance(effect, str) and effect:
            suffix = _slash(_ACCESSIBILITY.get(effect.lower(), effect))
            self.transform = _slash(self.transform) + suffix
            if self.thumb:
                self.thumb = _slash(self.thumb) + suffix

    def url(self, url: str, prefix: str, transform: str) -> str:
        path = _path(url)
        if not path.endswith(_MEDIA_EXTENSIONS):
            return url
        if self.svg and path.endswith(".svg"):
            transform = self.svg
        transform = _slash(transform) if transform else transform
        asset = url[len(prefix) :].lstrip("/")
        base = f"https://res.cloudinary.com/{self.cloud}/image/upload/"
        return f"{base}{transform}{self.mapping[prefix]}/{asset}"

    def image(self, tag: Tag) -> bool:
        src = tag.get("src")
        if not isinstance(src, str) or not src:
            return False
        prefix = next((p for p in self.mapping if src.startswith(p)), None)
        if not prefix:
            return False
        if tag.get("srcset"):
            del tag["srcset"]
        if self.lazyload in ("true", "native", "observer"):
            tag["loading"] = "lazy"
        opted_out = str(tag.get("data-cld-responsive", "")).strip().lower() == "false"
        if _path(src).endswith(".svg"):
            tag["src"] = self.url(src, prefix, self.svg)
        elif opted_out or not self.enabled:
            tag["src"] = self.url(src, prefix, self.static if opted_out else self.transform)
        else:
            existing = tag.get("class")
            classes = existing.split() if isinstance(existing, str) else list(existing or [])
            if "cld-responsive" not in classes:
                classes.append("cld-responsive")
            tag["class"] = " ".join(classes)
            tag["data-src"] = self.url(src, prefix, self.transform)
            tag["src"] = _BLANK_GIF if self.blank else self.url(src, prefix, self.thumb)
        return True

    def _replace_prefix(self, text: str, prefix: str) -> str:
        def replace(match: re.Match[str]) -> str:
            # The toolkit checks the preceding 150 characters for a containing Cloudinary URL.
            before = text[max(0, match.start() - 150) : match.start()]
            _, domain, tail = before.rpartition("res.cloudinary.com")
            if domain and not any(char in tail for char in " \"')><\n\t"):
                return match[0]
            return self.url(match[0], prefix, self.transform)

        return re.sub(re.escape(prefix) + r"""[^\s"')>]*""", replace, text)

    def text(self, text: str) -> str:
        for prefix in self.mapping:
            if prefix in text:
                text = self._replace_prefix(text, prefix)
        return text


def apply_cloudinary(soup: BeautifulSoup, config: dict[str, Any]) -> None:
    """Rewrite the parsed page and append its selected responsive script."""
    if not config.get("cl_map"):
        return
    delivery = _Delivery(config)
    for tag in soup.find_all(True):
        if tag.name == "script" or (tag.name == "img" and delivery.image(tag)):
            continue
        for attr, value in tag.attrs.items():
            if isinstance(value, str) and not (tag.name == "img" and attr in ("src", "data-src")):
                tag[attr] = delivery.text(value)
        if tag.name == "style" and tag.string:
            tag.string = delivery.text(tag.string)
    if delivery.enabled:
        append_responsive_script(
            soup, delivery.cloud, delivery.responsive, delivery.methodology, delivery.lazyload
        )


def process_html_cloudinary(html: str, config: dict[str, Any]) -> str:
    """Apply only the toolkit's Cloudinary step, preserving the input if mapping is off."""
    if not config.get("cl_map"):
        return html
    soup = BeautifulSoup(html, "html.parser")
    apply_cloudinary(soup, config)
    return str(soup)
