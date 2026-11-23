# this_file: src/vexy_mkdocs_page_import/plugin.py
"""Replace the final page output after navigation and search have seen the Markdown."""

import math
from pathlib import Path

from mkdocs.config.defaults import MkDocsConfig
from mkdocs.exceptions import PluginError
from mkdocs.plugins import BasePlugin, event_priority, get_plugin_logger
from mkdocs.structure.pages import Page

from .api import import_keys
from .cloudinary import cloud_name
from .config import PageImportConfig
from .fetch import fetch
from .webflow import insert_head, process_webflow

log = get_plugin_logger(__name__)


class PageImportPlugin(BasePlugin[PageImportConfig]):  # type: ignore[no-untyped-call]
    def on_config(self, config: MkDocsConfig) -> None:  # noqa: ARG002
        timeout = self.config.timeout
        if isinstance(timeout, bool) or not math.isfinite(timeout) or timeout <= 0:
            raise PluginError("page-import: timeout must be a positive, finite number of seconds")
        if isinstance(self.config.max_bytes, bool) or self.config.max_bytes <= 0:
            raise PluginError("page-import: max_bytes must be a positive integer")
        if self.config.webflow.cloudinary.get("cl_map"):
            cloud_name(self.config.webflow.cloudinary)

    @event_priority(-100)
    def on_post_page(self, output: str, *, page: Page, config: MkDocsConfig) -> str:
        name = page.file.src_uri
        try:
            selection = import_keys(page.meta)
        except ValueError as exc:
            raise PluginError(f"{name}: {exc}") from exc
        if selection is None:
            return output
        key, source = selection
        try:
            config_dir = Path(config.config_file_path or config.docs_dir).parent
            return self._import_page(key, source, config_dir, name, output)
        except (OSError, ValueError, PluginError) as exc:
            raise PluginError(f"{name}: {key}: {exc}") from exc

    def _import_page(
        self, key: str, source: str, config_dir: Path, page_name: str, output: str
    ) -> str:
        if key == "copy-file":
            if Path(source).is_absolute():
                raise PluginError("copy-file requires a relative path inside copy_root")
            try:
                root = (config_dir / self.config.copy_root).resolve()
                path = (config_dir / source).resolve()
            except RuntimeError as exc:  # Python 3.12 reports symlink loops as RuntimeError.
                raise PluginError(f"cannot resolve copy-file or copy_root: {exc}") from exc
            if root not in path.parents:
                raise PluginError(f"{path} must be inside copy_root {root}")
            html = path.read_bytes().decode("utf-8")
            if not html.strip():
                raise PluginError(f"empty HTML in {source}")
        else:
            imported = fetch(source, config_dir, self.config)
            if imported is None:
                log.info("%s: offline cache miss; keeping rendered page", page_name)
                return output
            html = imported
        if key == "webflow-import-url":
            return process_webflow(
                html, self.config.webflow, self.config.inject_head, page_name=page_name
            )
        return insert_head(html, self.config.inject_head, page_name=page_name)
