---
this_file: DEPENDENCIES.md
---

# Dependencies

| Dependency | Purpose |
| --- | --- |
| MkDocs | Provides the plugin event, typed configuration, build errors and logging. The compatibility suite uses 1.6.1. |
| beautifulsoup4 | Parses and edits Webflow HTML with Python’s built-in `html.parser`. |
| ProperDocs 1.6.7 | Alternative site builder used in the compatibility suite. Install it alongside the plugin to use its CLI. |
| hatchling | Builds the wheel and source distribution from the `src/` layout. |
| hatch-vcs | Derives the version from Git and generates `__version__.py` during a build. |
| pytest | Runs the fixture site builds and HTML transformation tests. |
| pytest-cov | Measures coverage of the plugin during test runs. |
| markdownify | Development dependency needed to import the reference builder in Cloudinary parity tests. |
| ruff | Checks and formats the Python source and tests. |
| mypy | Statically checks the package in strict mode. |

HTTP requests, hashing, temporary files and the loopback test server use the
Python standard library.
