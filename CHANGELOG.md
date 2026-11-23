---
this_file: CHANGELOG.md
---

# Changelog

## Unreleased

- Added `on_offline_miss: keep` to retain the rendered Markdown when a URL has no usable cached HTML. The default remains `error`.
- Documented and tested `enabled: false` for builds that skip all imports. Exported `cache_path`, `read_cached`, and `import_keys` for Python build tools.
- Added page replacement from a URL, a Webflow export, or a local HTML file.
- Added a disk cache for offline builds, retry and fallback on fetch errors, and optional head HTML.
- Added Webflow badge removal, Google Fonts link splitting, Cloudinary media rewriting, and Rocket Loader opt-out.
- Added the toolkit’s complete Cloudinary configuration under `webflow.cloudinary`, including modern and legacy responsive scripts, thumbnail and accessibility transformations, lazy loading, placeholders, and per-page Cloudinary overrides. Existing flat Cloudinary settings remain supported.
