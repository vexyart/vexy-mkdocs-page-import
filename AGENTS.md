---
this_file: AGENTS.md
---

# Development

The plugin lives in `src/vexy_mkdocs_page_import/`. Its `on_post_page` hook
replaces the final HTML. The fetcher caches source HTML so Webflow and head
options can be changed on an offline build.

`tests/test_build.py` uses an actual site builder and a loopback HTTP server.
`tests/test_webflow.py` covers transformations on individual HTML documents.

Run from the project root on Python 3.13.

```sh
uv venv --python 3.13
uv pip install -e ".[dev]" "mkdocs==1.6.1" "properdocs==1.6.7"
uv run pytest -q
uv run python -c 'import properdocs.replacement; import pytest; raise SystemExit(pytest.main(["-q"]))'
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv build
```

The second pytest invocation selects the same MkDocs API aliases as the
ProperDocs CLI. The release wheel must contain the `mkdocs.plugins` entry
point `page-import` and the generated `__version__.py`.
