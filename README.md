---
this_file: README.md
---

# vexy-mkdocs-page-import

Publish a precompiled HTML page at a Markdown page’s usual URL. MkDocs or ProperDocs
renders the Markdown body for search and keeps the page in navigation. The
`page-import` plugin replaces the final page HTML, including the theme.

## Install

Requires Python 3.12 or later. From the package checkout, install into the
environment used to build your site.

```sh
uv pip install .
```

Enable the plugin in `mkdocs.yml`. Include `search` if you want the Markdown indexed.

```yaml
site_name: Project handbook
plugins:
  - search
  - page-import:
      refresh: true
      inject_head: '<meta name="application-name" content="Project handbook">'
      webflow:
        cloudinary:
          cl_cloud: fontlab
          cl_map:
            "https://cdn.example.org/media": handbook
          cl_trans: "c_limit,w_auto/f_auto,q_auto,dpr_auto/"
          cl_responsive:
            methodology: modern
            lazyload: observer
            placeholder: blur
            cl_trans_thumb: "c_limit,w_128/f_auto,q_1/"
            cl_core_js: "https://unpkg.com/cloudinary-core@latest"
```

## Select a page source

Use at most one of these keys in a page’s YAML front matter.

| Key | Value |
| --- | --- |
| `import-url` | HTTP or HTTPS URL of the precompiled page. |
| `webflow-import-url` | HTTP or HTTPS URL of a Webflow page. Applies the Webflow options below. |
| `copy-file` | Path to a UTF-8 HTML file, relative to the directory containing the site configuration. |

For example, `docs/guide.md` can contain the following text.

```markdown
---
title: Installation guide
copy-file: exports/installation.html
---

# Installation guide

Find the installer and choose a destination folder.
```

The guide appears in navigation, and its Markdown text appears in the search index.
Visitors opening the guide see the contents of `exports/installation.html`.
Asset links in imported HTML resolve against the published URL. Use absolute URLs
or supply the assets at their referenced paths.

## Options

| Option | Default | Behaviour |
| --- | --- | --- |
| `enabled` | `true` | Set to `false` to render the Markdown normally and skip all page imports, including cache access. |
| `timeout` | `30` | Timeout in seconds for a network operation during a fetch. |
| `copy_root` | `.` | Directory allowed for `copy-file` imports. Relative paths for both settings start at the site configuration directory. The file must be inside `copy_root` after resolving symlinks. |
| `cache_dir` | `.cache/page-import` | Cache directory relative to the site configuration. Each URL has one entry keyed by the SHA-256 of the URL. |
| `offline` | `false` | Read URL imports from cache only. |
| `on_offline_miss` | `error` | With `offline: true`, `error` fails the build on a cache miss. `keep` logs the page name at INFO and keeps its rendered Markdown. |
| `refresh` | `true` | Fetch again when online. Set to `false` to fetch only on a cache miss. |
| `inject_head` | `""` | Insert HTML before the first closing head tag in any imported page. An existing copy is skipped. A missing closing tag produces a warning naming the page. |
| `webflow.strip_badge` | `true` | Remove badge anchors and insert the hiding style. |
| `webflow.badge_hide_css` | `<style>.w-webflow-badge{display:none !important;}</style>` | Override the badge style. A headless fragment gets the style at the start and a warning naming the page. |
| `webflow.split_google_fonts` | `true` | Split Google Fonts CSS2 links with multiple family parameters, preserving other query parameters on each link. |
| `webflow.cloudinary` | `{}` | Cloudinary delivery settings. Paste the toolkit’s `cloudinary` block under `webflow`. |
| `webflow.rocket_loader_optout` | `true` | Set `data-cfasync="false"` on classic JavaScript and module scripts. Data scripts such as JSON and JSON-LD are skipped. An existing `data-cfasync` value is preserved. |

URL imports follow HTTP and HTTPS redirects and make up to three attempts with
short backoff. An HTTP 4xx response ends the fetch on the first attempt. If the
fetch fails, the plugin warns and uses a readable cached page, or fails the build
on a cache miss. A corrupt or unreadable entry counts as a miss. The cache holds
the source HTML, so changes to Webflow options and head markup also take effect
offline. Supply a nonempty HTML document for each import.

## Python API

Build tools can inspect front matter and cached HTML without starting MkDocs.
Import the helpers directly from `vexy_mkdocs_page_import`.

```python
from pathlib import Path
from vexy_mkdocs_page_import import cache_path, import_keys, read_cached

cache_dir = Path("handbook/.cache/page-import")
source = import_keys({"webflow-import-url": "https://example.org/guide"})
if source and source[0] in {"import-url", "webflow-import-url"}:
    url = source[1]
    path = cache_path(cache_dir, url)
    html = read_cached(cache_dir, url)
```

- `cache_path(cache_dir: Path, url: str) -> Path` returns the plugin’s cache filename for the exact URL. It does no I/O.
- `read_cached(cache_dir: Path, url: str) -> str | None` reads the UTF-8 source HTML. A missing, unreadable, invalid UTF-8, or blank entry returns `None`. Pass the cache directory itself to both helpers.
- `import_keys(meta: Mapping[str, object]) -> tuple[str, str] | None` returns the single import key and its value, or `None` if absent. Multiple keys or a value other than a nonempty string raise `ValueError`.

## Cloudinary delivery

Set `cl_cloud` to the cloud containing your assets and `cl_map` to a mapping of source
URL prefixes to Cloudinary folders. The first matching prefix wins. An empty map
disables rewriting and script injection. The defaults for `cl_cloud` and `cl_trans`
are shown in the example. Existing `webflow.cl_cloud`, `webflow.cl_trans` and
`webflow.cl_map` settings work as aliases. A key in `webflow.cloudinary` takes
precedence over the same flat key.

Without `cl_responsive`, mapped images get a static URL. Set it to `true` or
a nonempty mapping to enable responsive delivery. A mapped raster image then
gets a placeholder in `src`, the full delivery URL in `data-src`, and the class
`cld-responsive`. The old `srcset` is removed. Mapped SVG images use
`cl_trans_svg` (default `f_svg,q_auto`), and raster images marked
`data-cld-responsive="false"` use `cl_trans_static` (default `f_auto,q_auto`).
Media URLs in HTML attributes and CSS also get rewritten.

| Inside `cl_responsive` | Behaviour |
| --- | --- |
| `methodology` | `modern` (default) emits a resize observer that adjusts image width for the displayed size and device pixel ratio. `legacy` loads Cloudinary Core and calls `cl.responsive()`. |
| `lazyload` | `false` (default) omits lazy-loading attributes. `native` sets `loading="lazy"`. `observer` also uses an intersection observer with the modern script. `true` selects observer for modern and native for legacy. |
| `placeholder` | Use `blur`, `pixelate`, `vectorize`, `predominant`, `predominant-color`, or a custom transformation. `false` uses a transparent GIF. Leaving it unset uses `cl_trans_thumb`. |
| `accessibility` | Append `colorblind`, `monochrome`, `darkmode`, `brightmode`, or a custom effect to the full image and placeholder transformations. |
| `cl_trans_thumb` | Default thumbnail transformation, `c_limit,w_128/f_auto,q_1/`. |
| `cl_core_js` | Cloudinary Core script URL for legacy mode. The example shows its default. |
| `cl_custom_js` | Replace the built-in modern script with JavaScript source or script markup. |

With responsive mode off, the toolkit reads `lazyload`, `placeholder`, and
`accessibility` directly under `cloudinary`. Static images use a single URL,
so they have no placeholder. A Webflow export can override Cloudinary settings
in a JSON script with `id="fontlab-toolkit-config"` and `type="application/json"`.
Its `cloudinary` object replaces matching site settings one key at a time,
including the whole `cl_map` or `cl_responsive` value when supplied.

Licensed under Apache-2.0.
