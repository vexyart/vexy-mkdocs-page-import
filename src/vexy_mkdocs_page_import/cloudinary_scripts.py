# this_file: src/vexy_mkdocs_page_import/cloudinary_scripts.py
"""Emit the toolkit's responsive image scripts with their original whitespace."""

import json
from string import Template
from typing import Any

from bs4 import BeautifulSoup

_CORE_JS = "https://unpkg.com/cloudinary-core@2.14.1/cloudinary-core.js"
_CORE_SRI = "sha384-yP73KpugzJHZ1Fek8lpAVOTPfOT5iU/ov7zdYEyi7+U2KT9rvIqZKcWz/a2veMTe"
_INTERSECTION = """\
    const intersectionObserver = new IntersectionObserver((entries, observer) => {
      for (let entry of entries) {
        if (entry.isIntersecting) {
          const img = entry.target;
          observer.unobserve(img);
          resizeObserver.observe(img);
        }
      }
    }, { rootMargin: '50px' });
"""
_MODERN_SCRIPT = Template(
    """
(function() {
  function initResponsive() {
    const $resize = new ResizeObserver(entries => {
      for (let entry of entries) {
        const img = entry.target;
        const width = img.clientWidth || (img.parentElement ? img.parentElement.clientWidth : 0);
        if (width > 0) {
          const dpr = window.devicePixelRatio || 1;
          const targetWidth = Math.ceil((width * dpr) / 100) * 100;
          const dataSrc = img.getAttribute('data-src');
          if (dataSrc) {
            const newSrc = dataSrc.replace('w_auto', 'w_' + targetWidth);
            if (img.getAttribute('src') !== newSrc) {
              img.style.transition = 'filter 0.4s ease-in-out';
              img.style.filter = 'blur(4px)';
              const handleLoad = () => {
                img.style.filter = 'none';
                img.removeEventListener('load', handleLoad);
              };
              img.addEventListener('load', handleLoad);
              img.setAttribute('src', newSrc);
              if (img.complete) {
                handleLoad();
              }
            }
          }
        }
      }
    });
$intersection    document.querySelectorAll('img.cld-responsive').forEach(img => {
      $observe.observe(img);
    });
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initResponsive);
  } else {
    initResponsive();
  }
})();
"""
)


def append_responsive_script(
    soup: BeautifulSoup,
    cl_cloud: str,
    cl_responsive: dict[str, Any],
    methodology: str,
    effective_lazyload: str,
) -> None:
    """Append the configured script to the body or to the end of an HTML fragment."""
    body = soup.body or soup
    script = soup.new_tag("script", type="text/javascript")
    if methodology == "legacy":
        core = cl_responsive.get("cl_core_js", _CORE_JS)
        library = soup.new_tag("script", src=core, type="text/javascript")
        if core == _CORE_JS:
            library["integrity"] = _CORE_SRI
            library["crossorigin"] = "anonymous"
        body.append(library)
        # Raw HTML script text must also escape the opening < of a closing script tag.
        name = json.dumps(cl_cloud).replace("<", "\\u003c")
        script.string = (
            f"\nvar cl = cloudinary.Cloudinary.new({{cloud_name: {name}}});\ncl.responsive();\n"
        )
    elif custom := cl_responsive.get("cl_custom_js"):
        if custom.strip().startswith("<script"):
            # Moving nodes from the live contents list matches the toolkit's fragment handling.
            for node in BeautifulSoup(custom, "html.parser").contents:
                body.append(node)
            return
        script.string = f"\n{custom}\n"
    else:
        deferred = effective_lazyload == "observer"
        script.string = _MODERN_SCRIPT.substitute(
            resize="resizeObserver" if deferred else "observer",
            intersection=_INTERSECTION if deferred else "",
            observe="intersectionObserver" if deferred else "observer",
        )
    body.append(script)
