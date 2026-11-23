# this_file: src/vexy_mkdocs_page_import/__init__.py
"""Import precompiled HTML into MkDocs and ProperDocs sites."""

from .api import cache_path, import_keys, read_cached

__all__ = ["__version__", "cache_path", "import_keys", "read_cached"]

try:
    from .__version__ import __version__ as __version__
except ImportError:
    __version__ = "0.0.0"
