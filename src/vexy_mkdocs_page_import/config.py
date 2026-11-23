# this_file: src/vexy_mkdocs_page_import/config.py
"""Configuration validated by MkDocs before the build starts."""

from mkdocs.config import config_options as c
from mkdocs.config.base import Config

from .api import DEFAULT_MAX_BYTES


class WebflowConfig(Config):  # type: ignore[no-untyped-call]
    strip_badge = c.Type(bool, default=True)
    badge_hide_css = c.Type(
        str, default="<style>.w-webflow-badge{display:none !important;}</style>"
    )
    split_google_fonts = c.Type(bool, default=True)
    cloudinary = c.Type(dict, default={})
    rocket_loader_optout = c.Type(bool, default=True)


class PageImportConfig(Config):  # type: ignore[no-untyped-call]
    timeout = c.Type((int, float), default=30)
    max_bytes = c.Type(int, default=DEFAULT_MAX_BYTES)
    cache_dir = c.Type(str, default=".cache/page-import")
    copy_root = c.Type(str, default=".")
    offline = c.Type(bool, default=False)
    on_offline_miss = c.Choice(("error", "keep"), default="error")
    refresh = c.Type(bool, default=True)
    inject_head = c.Type(str, default="")
    webflow = c.SubConfig(WebflowConfig)
