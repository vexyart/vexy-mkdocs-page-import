---
this_file: CHANGELOG.md
---

# Changelog

## 0.1.0 — 2026-11-23

- Publish whole HTML documents from URLs, Webflow exports, or files under `copy_root`, with optional head markup.
- Cache source HTML for offline builds and strict-build fallback. Bound online fetches by time and size, redact URL queries and fragments in diagnostics, and refuse HTTPS downgrades.
- Online fetches use the runtime dependencies `aiohttp` and `yarl`. `aiohttp` handles network I/O under one deadline per attempt, including DNS resolution, headers and body reads. `yarl` resolves redirect URLs and redacts URLs in diagnostics.
- Offline builds leave `aiohttp` unloaded. Ctrl-C cancels an active download and returns control to the caller.
- Clean up Webflow badges and fonts, opt scripts out of Rocket Loader, and configure responsive media under `webflow.cloudinary` or in a page's `page-import-config` JSON.
- When migrating from `fontlab-www-toolkit`, rename the inline JSON script ID from `fontlab-toolkit-config` to `page-import-config`.
- Export typed `fetch_url`, `cache_path`, `read_cached`, `refresh_cache`, and `import_keys` helpers. `refresh_cache` atomically replaces the entry after a successful fetch.
