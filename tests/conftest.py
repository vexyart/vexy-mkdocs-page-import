# this_file: tests/conftest.py
"""Build sites from real config files and serve controlled HTTP responses on loopback."""

import json
import ssl
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from threading import Thread

import pytest
from mkdocs.commands.build import build
from mkdocs.config import load_config
from mkdocs.exceptions import Abort, PluginError

HTML = '<html><head></head><body><script src="app.js"></script>Imported café</body></html>'


@pytest.fixture(autouse=True)
def bypass_proxy_for_loopback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("no_proxy", "127.0.0.1,localhost")


@dataclass
class Origin:
    url: str = ""
    html: str = HTML
    body: bytes | None = None
    failures: int = 0
    error_code: int = 503
    redirect: str = ""
    agents: list[str] = field(default_factory=list)


@contextmanager
def serve(
    handler: type[BaseHTTPRequestHandler], tls: ssl.SSLContext | None = None
) -> Iterator[str]:
    with HTTPServer(("127.0.0.1", 0), handler) as http:
        if tls is not None:
            http.socket = tls.wrap_socket(http.socket, server_side=True)
        thread = Thread(target=http.serve_forever, kwargs={"poll_interval": 0.01})
        thread.start()
        try:
            yield f"{'https' if tls else 'http'}://127.0.0.1:{http.server_port}"
        finally:
            http.shutdown()
            thread.join()


@pytest.fixture
def origin() -> Iterator[Origin]:
    state = Origin()

    class Request(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            state.agents.append(self.headers.get("User-Agent", ""))
            if state.failures:
                state.failures -= 1
                self.send_error(state.error_code)
                return
            if state.redirect and self.path.partition("?")[0] == "/page":
                self.send_response(302)
                self.send_header("Location", state.redirect)
                self.end_headers()
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(state.html.encode() if state.body is None else state.body)

        def log_message(self, *_args: object) -> None:
            pass  # Expected 503s should stay out of the test output.

    with serve(Request) as base:
        state.url = f"{base}/page"
        yield state


def build_page(root: Path, meta: dict[str, object], **options: object) -> str:
    docs = root / "docs"
    docs.mkdir(exist_ok=True)
    (docs / "index.md").write_text("# Home\n\nOrdinary page.", encoding="utf-8")
    front = "\n".join(f"{key}: {json.dumps(value)}" for key, value in meta.items())
    (docs / "imported.md").write_text(
        f"---\n{front}\n---\n# Searchable heading\n\nSearchable Markdown body.", encoding="utf-8"
    )
    theme = root / "theme"
    theme.mkdir(exist_ok=True)
    (theme / "main.html").write_text(
        '<nav>{% for item in nav %}<a href="{{ item.url | url }}">{{ item.title }}</a>'
        "{% endfor %}</nav>{{ page.content }}",
        encoding="utf-8",
    )
    config = root / "mkdocs.yml"
    config.write_text(
        "site_name: Import test\ntheme: {name: null, custom_dir: theme}\n"
        "nav: [index.md, imported.md]\nplugins:\n  - search\n"
        f"  - page-import: {json.dumps(options)}\n",
        encoding="utf-8",
    )
    try:
        build(load_config(config_file=str(config)))
    except Abort as exc:
        # MkDocs wraps plugin build failures in Abort at its CLI boundary.
        if isinstance(exc.__context__, PluginError):
            raise exc.__context__ from None
        raise
    return (root / "site/imported/index.html").read_text(encoding="utf-8")
