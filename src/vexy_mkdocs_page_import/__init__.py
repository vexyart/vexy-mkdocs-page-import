# this_file: src/vexy_mkdocs_page_import/__init__.py
"""Import precompiled HTML into MkDocs and ProperDocs sites."""

try:
    from .__version__ import __version__ as __version__
except ImportError:
    __version__ = "0.0.0"
