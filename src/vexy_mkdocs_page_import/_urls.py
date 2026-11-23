# this_file: src/vexy_mkdocs_page_import/_urls.py
"""Validate source URLs and redact diagnostics for online and offline imports."""

from yarl import URL


def checked_url(url: str) -> URL:
    try:
        if any(char <= " " or char == "\x7f" for char in url):
            raise ValueError
        parsed = URL(url, encoded=True)
        if parsed.scheme in {"http", "https"} and parsed.host:
            return parsed
    except ValueError:
        pass
    raise ValueError("expected an HTTP or HTTPS URL")


def display_url(url: URL) -> str:
    return str(url.with_query(None).with_fragment(None).with_user(None))
