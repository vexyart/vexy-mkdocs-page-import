---
this_file: CHANGELOG.md
---

# Changelog

## 0.1.0 — 2026-11-23

- Publish whole HTML documents from URLs, Webflow exports, or files under `copy_root`, with optional head markup.
- Cache source HTML for offline builds and strict-build fallback. Bound online fetches by time and size, redact URL queries and fragments in diagnostics, and refuse HTTPS downgrades.
- Clean up Webflow badges and fonts, opt scripts out of Rocket Loader, and configure responsive media under `webflow.cloudinary` or in a page's `page-import-config` JSON.
- Export typed `fetch_url`, `cache_path`, `read_cached`, and `import_keys` helpers.
