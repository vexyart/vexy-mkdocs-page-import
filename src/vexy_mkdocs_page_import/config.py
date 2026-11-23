# this_file: src/vexy_mkdocs_page_import/config.py
"""Configuration validated by MkDocs before the build starts."""

from mkdocs.config import config_options as c
from mkdocs.config.base import Config


class WebflowConfig(Config):  # type: ignore[no-untyped-call]
    strip_badge = c.Type(bool, default=True)
    badge_hide_css = c.Type(
        str, default="<style>.w-webflow-badge{display:none !important;}</style>"
    )
    split_google_fonts = c.Type(bool, default=True)
    cloudinary = c.Type(dict, default={})
    cl_map = c.DictOfItems(c.Type(str), default={})
    cl_trans = c.Type(str, default="c_limit,w_auto/f_auto,q_auto,dpr_auto/")
    cl_cloud = c.Type(str, default="fontlab")
    rocket_loader_optout = c.Type(bool, default=True)


class PageImportConfig(Config):  # type: ignore[no-untyped-call]
    timeout = c.Type((int, float), default=30)
    cache_dir = c.Type(str, default=".cache/page-import")
    copy_root = c.Type(str, default=".")
    offline = c.Type(bool, default=False)
    refresh = c.Type(bool, default=True)
    inject_head = c.Type(str, default="")
    webflow = c.SubConfig(WebflowConfig)
