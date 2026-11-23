# this_file: src/vexy_mkdocs_page_import/_download.py
"""Fetch a bounded HTTP response under one deadline across all redirect hops."""

import asyncio
import math
import sys
from concurrent.futures import Future, ThreadPoolExecutor, wait
from contextlib import closing, suppress
from urllib.request import getproxies, proxy_bypass

import aiohttp
from yarl import URL

from ._urls import checked_url, display_url

MAX_REDIRECTS = 10


class _ResponseError(ValueError):
    """A permanent failure with a message safe to display."""


def _proxy(url: URL) -> str | None:
    # Match urllib's proxy settings without sending credentials from the user's netrc.
    proxy = getproxies().get(url.scheme)
    host = url.host_port_subcomponent
    return proxy if proxy and host and not proxy_bypass(host) else None


def _redirect(url: URL, location: str) -> URL:
    try:
        target = checked_url(str(url.join(URL(location.replace(" ", "%20"), encoded=True))))
    except ValueError:
        raise _ResponseError("refused redirect: expected an HTTP or HTTPS URL") from None
    if url.scheme == "https" and target.scheme == "http":
        raise _ResponseError("refused HTTPS to HTTP redirect downgrade")
    return target


class _ServerError(Exception):
    """A 5xx status can succeed on a subsequent attempt."""


async def _read(session: aiohttp.ClientSession, url: URL, max_bytes: int) -> str:
    for _ in range(MAX_REDIRECTS + 1):
        proxy = await asyncio.to_thread(_proxy, url)
        async with session.get(url, allow_redirects=False, proxy=proxy) as response:
            if response.status in {301, 302, 303, 307, 308} and "Location" in response.headers:
                url = _redirect(url, response.headers["Location"])
                continue
            if response.status >= 500:
                raise _ServerError(f"HTTP {response.status}")
            if response.status >= 300:
                raise _ResponseError(f"HTTP {response.status}")
            try:
                await response.content.readexactly(max_bytes + 1)
            except asyncio.IncompleteReadError as exc:
                body = exc.partial
            else:
                raise _ResponseError(f"response exceeds max_bytes ({max_bytes})")
            try:
                html = body.decode(response.charset or "utf-8")
            except (UnicodeError, LookupError):
                raise _ResponseError(
                    "cannot decode HTML using its declared charset or UTF-8"
                ) from None
            if not html.strip():
                raise _ResponseError("empty HTML")
            return html
    raise _ResponseError("too many redirects")


async def _get(url: URL, timeout: float, retries: int, max_bytes: int) -> str:
    async with aiohttp.ClientSession(
        headers={"User-Agent": "vexy-mkdocs-page-import", "Accept-Encoding": "identity"},
        auto_decompress=False,
        cookie_jar=aiohttp.DummyCookieJar(),
        timeout=aiohttp.ClientTimeout(total=None),
    ) as session:
        attempt = 1
        while True:
            try:
                async with asyncio.timeout(timeout):
                    return await _read(session, url, max_bytes)
            except _ResponseError as exc:
                raise OSError(f"failed to fetch {display_url(url)}: {exc}") from None
            except ValueError:
                raise OSError(f"failed to fetch {display_url(url)}: invalid request") from None
            except (aiohttp.ClientError, TimeoutError, _ServerError) as exc:
                # Transport messages and HTTP reason phrases can echo the full request URI.
                reason = str(exc) if isinstance(exc, _ServerError) else type(exc).__name__
                if attempt > retries:
                    raise OSError(
                        f"failed to fetch {display_url(url)} after {attempt} attempt(s): {reason}"
                    ) from None
            await asyncio.sleep(0.1 * attempt)
            attempt += 1


def download(url: str, timeout: float, retries: int, max_bytes: int) -> str:
    parsed = checked_url(url)
    if isinstance(timeout, bool) or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("timeout must be a positive, finite number of seconds")
    if type(retries) is not int or retries < 0:
        raise ValueError("retries must be a nonnegative integer")
    if type(max_bytes) is not int or max_bytes < 1:
        raise ValueError("max_bytes must be a positive integer")

    interrupted: Future[None] = Future()

    def run() -> str:
        # Closing the loop leaves OS DNS resolution free to finish after a deadline.
        with closing(asyncio.new_event_loop()) as loop:
            task = loop.create_task(_get(parsed, timeout, retries, max_bytes))

            def cancel(_signal: Future[None]) -> None:
                # A completed download may have closed the loop as Ctrl-C arrived.
                with suppress(RuntimeError):
                    loop.call_soon_threadsafe(task.cancel)

            interrupted.add_done_callback(cancel)
            return loop.run_until_complete(task)

    # A synchronous build tool may already be running an asyncio loop in its calling thread.
    executor = ThreadPoolExecutor(max_workers=1)
    try:
        future = executor.submit(run)
        # Older Windows Pythons dispatch keyboard signals only after a timed wait returns.
        while sys.platform == "win32" and not future.done():
            wait((future,), timeout=0.1)
        return future.result()
    except KeyboardInterrupt:
        interrupted.cancel()
        raise
    finally:
        executor.shutdown(wait=False, cancel_futures=True)
