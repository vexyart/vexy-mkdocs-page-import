---
this_file: WORK.md
---

# Verification

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
