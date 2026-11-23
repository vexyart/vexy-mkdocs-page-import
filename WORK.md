---
this_file: WORK.md
---

# Verification

## Cache refresh and release checks — 2026-11-23

On Python 3.13, MkDocs and ProperDocs each passed 139 tests, up from 135 at
`79a0180`. Loopback tests verified atomic cache replacement, preservation of
the previous entry on a failed refresh, and an offline build in a fresh process
with `aiohttp` absent. On macOS a stalled download raised `KeyboardInterrupt`
and the process exited within three seconds of SIGINT while the server still
held the request. The interrupt test also passed on Python 3.12 and 3.14.
The Windows console-signal path received static review only.

Ruff passed lint and formatting (24 files), strict mypy passed (11 source files),
and actionlint accepted the release workflow. The release test job runs both
builders before the distribution build and publish jobs. The local wheel and
sdist passed strict Twine checks. Importing the plugin from the wheel exposed
`refresh_cache` and left `aiohttp` unloaded.

## 0.1.0 release readiness — 2026-11-23

The baseline passed 109 tests. After the release fixes, all 135 tests passed on
each combination of Python 3.12.12, 3.13.18 and 3.14.10 with MkDocs 1.6.1 and
ProperDocs 1.6.7. The suite includes a real HTTPS downgrade, slow headers,
slow bodies, a cumulative redirect deadline, and a strict CLI build serving a
cached page after a 404. OpenSSL generates a temporary loopback certificate.

Ruff lint and formatting passed (23 Python files), strict mypy passed (10 source
files), and actionlint accepted both workflows. The locked dev environment
resolved 42 packages. The ordinary untagged build and a separate build with
`SETUPTOOLS_SCM_PRETEND_VERSION=0.1.0` each produced a wheel and sdist that
passed `twine check --strict`. Both wheels contained the type marker and generated
version module. Both sdists contained all 12 golden HTML files. A fresh install
of the 0.1.0 preview loaded the plugin entry point and four public helpers, and
`mkdocs build --strict` preserved the local import's UTF-8 and CRLF bytes.

The golden files came from the toolkit's `origin/main` commit
`2b054e66579f7d4899f949a19ecc3031e77f2641` (reference source SHA-256 below).
They capture six inputs before and after whole-page processing. The two expected
differences in the comparisons are the inline config ID and JSON string quoting.

Both consumer configurations already nest the three Cloudinary keys. A
read-only scan found zero occurrences of the old config ID in 26 cached and
five static FontLab files, and 20 cached and one static Vexy file.

## Build controls and Python API

Both MkDocs 1.6.1 and ProperDocs 1.6.7 passed 109 tests. Disabled builds and
offline misses with `keep` produced the same HTML as an ordinary Markdown build.
Ruff lint and formatting passed, and strict mypy checked nine source files.
The wheel’s three public helpers also passed a cache round trip in an isolated
Python interpreter with site packages disabled.

## Responsive Cloudinary delivery

The full suite passed on MkDocs 1.6.1 and ProperDocs 1.6.7 (93 tests each).
Six cases compared both the Cloudinary transform and the published HTML file,
byte for byte, against the local toolkit. The comparisons include compact HTML
with a doctype and multi-family Google Fonts links, where reparsing between
transformations changes whitespace. No reference cases were skipped.

The reference `builder.py` had SHA-256
`4981c513738c499f65195e9fbeed253b541e25a9807db24b7440b8f9dc52728e`.
Ruff lint and formatting passed. Strict mypy checked eight source files.

## Initial package

Python 3.13.18, from the editable package and its installed wheel.
The gate commands are in [AGENTS.md](AGENTS.md).

| Check | Result |
| --- | --- |
| MkDocs 1.6.1 | 41 tests passed |
| ProperDocs 1.6.7, using its MkDocs API aliases | 41 tests passed |
| Ruff | Lint and formatting passed |
| mypy | Strict check passed for six source files |
| Distribution build | Built the source distribution and then the wheel from it |
| Wheel inspection | All six Python modules matched the source tree, including the generated version module. The installed `page-import` entry point loaded. |
| Installed-wheel CLI builds | Both builders passed `build --strict`. The imported HTML matched the local source byte for byte, including CRLF, and the search index contained the Markdown body. |

Tests serve remote imports on loopback. They count requests to verify cache hits,
offline operation, retries and fallback. Regression cases cover strings resembling
a closing head tag in JavaScript, comments and attributes, as well as remapping
an explicitly selected Cloudinary source prefix.

The first build in the uncommitted repository produced version
`0.0.1.dev0+d20261123`. The configured hatch-vcs fallback is `0.0.0`.
