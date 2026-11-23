# this_file: tests/test_download.py
"""Check the public fetcher against loopback HTTP and HTTPS responses."""

import asyncio
import os
import ssl
import subprocess
import sys
import time
from http.server import BaseHTTPRequestHandler
from pathlib import Path

import pytest
from conftest import HTML, Origin, serve

from vexy_mkdocs_page_import import fetch_url


def test_fetch_url_when_called_from_running_event_loop_then_downloads_html(origin: Origin) -> None:
    async def caller() -> str:
        return fetch_url(origin.url, retries=0, max_bytes=len(HTML.encode()))

    assert asyncio.run(caller()) == HTML


@pytest.mark.parametrize(("body", "reason"), [(b"12345", "max_bytes"), (b"\xff", "decode")])
def test_fetch_url_when_body_invalid_then_fails_once(
    origin: Origin, body: bytes, reason: str
) -> None:
    origin.body = body
    with pytest.raises(OSError, match=reason):
        fetch_url(origin.url, max_bytes=4)
    assert len(origin.agents) == 1


def test_fetch_url_when_retries_requested_then_honors_budget_and_redacts(origin: Origin) -> None:
    origin.failures = 10
    with pytest.raises(OSError, match="503") as exc:
        fetch_url(origin.url + "?hidden-query#hidden-fragment", retries=1)
    assert len(origin.agents) == 2
    assert "hidden-" not in str(exc.value)


@pytest.mark.parametrize("stage", ["headers", "body"])
def test_fetch_url_when_response_drips_then_stops_at_deadline(stage: str) -> None:
    class Drip(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            try:
                self.wfile.write(b"HTTP/1.0 200 OK\r\n")
                self.wfile.write(b"X-Slow: " if stage == "headers" else b"\r\n")
                for _ in range(100):
                    self.wfile.write(b"x")
                    time.sleep(0.03)
                self.wfile.write(b"\r\n\r\nend")
            except (BrokenPipeError, ConnectionResetError):
                pass

    with serve(Drip) as url:
        start = time.monotonic()
        with pytest.raises(OSError, match="TimeoutError"):
            fetch_url(url, retries=0, timeout=0.2)
        assert time.monotonic() - start < 1.5


def test_fetch_url_when_https_redirects_to_http_then_refuses_before_request(
    tmp_path: Path, origin: Origin
) -> None:
    key = tmp_path / "test.key"
    cert = tmp_path / "test.pem"
    config = tmp_path / "openssl.cnf"
    config.write_text(
        "[req]\nprompt=no\ndistinguished_name=dn\nx509_extensions=ext\n"
        "[dn]\nCN=127.0.0.1\n[ext]\nsubjectAltName=IP:127.0.0.1\n"
        "basicConstraints=critical,CA:TRUE\nkeyUsage=critical,digitalSignature,keyCertSign\n"
        "subjectKeyIdentifier=hash\nauthorityKeyIdentifier=keyid:always\n"
    )
    subprocess.run(
        [
            *"openssl req -x509 -newkey rsa:2048 -nodes -days 1 -config".split(),
            str(config),
            "-keyout",
            str(key),
            "-out",
            str(cert),
        ],
        check=True,
        capture_output=True,
    )
    tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    tls.load_cert_chain(cert, key)
    visits = []

    class Redirect(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            visits.append(self.path)
            self.send_response(302)
            self.send_header("Location", origin.url + "?secret-target")
            self.end_headers()

    with serve(Redirect, tls) as url:
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import sys; from vexy_mkdocs_page_import import fetch_url; fetch_url(sys.argv[1])",
                url + "/page?secret-source#secret-fragment",
            ],
            env={**os.environ, "SSL_CERT_FILE": str(cert), "NO_PROXY": "127.0.0.1"},
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
        )
    assert result.returncode != 0 and "HTTPS to HTTP redirect downgrade" in result.stderr
    assert "secret-" not in result.stderr
    assert visits == ["/page?secret-source"] and not origin.agents


def test_fetch_url_when_body_arrives_in_fragments_then_enforces_total_byte_count() -> None:
    class Fragments(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ab")
            time.sleep(0.05)
            self.wfile.write(b"cd")

    with serve(Fragments) as url:
        assert fetch_url(url, max_bytes=4) == "abcd"
        with pytest.raises(OSError, match="max_bytes"):
            fetch_url(url, max_bytes=3)


def test_fetch_url_when_redirects_accumulate_delay_then_deadline_covers_whole_attempt() -> None:
    class RedirectChain(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            time.sleep(0.12)
            self.send_response(302)
            self.send_header("Location", "/another")
            self.end_headers()

    with serve(RedirectChain) as url:
        with pytest.raises(OSError, match="TimeoutError"):
            fetch_url(url, retries=0, timeout=0.2)
