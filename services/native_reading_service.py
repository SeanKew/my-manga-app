"""Helpers for a native-style reader and basic WebView ad filtering.

Image extraction only reads ordinary HTTP(S) <img> elements present in the
currently open page. It does not bypass paywalls, authentication, DRM, or
site-side access controls. The cosmetic filter hides common ad containers and
blocks navigation to a small, explicit set of known ad-serving hosts; it is
not a full network-request blocker.
"""
from __future__ import annotations

import json
from urllib.parse import urljoin, urlparse

IMAGE_MESSAGE_PREFIX = "MANGAAPP_IMAGE_LIST:"

AD_BLOCK_LINK_PREFIXES = [
    "https://doubleclick.net/",
    "https://www.doubleclick.net/",
    "http://doubleclick.net/",
    "https://googleads.g.doubleclick.net/",
    "https://pagead2.googlesyndication.com/",
    "https://tpc.googlesyndication.com/",
    "https://www.googleadservices.com/",
    "https://adservice.google.com/",
    "https://securepubads.g.doubleclick.net/",
    "https://ads.pubmatic.com/",
    "https://servedby.flashtalking.com/",
    "https://trc.taboola.com/",
    "https://www.taboola.com/",
    "https://outbrain.com/",
    "https://www.outbrain.com/",
]

COSMETIC_AD_FILTER_JS = r"""(() => {
  const styleId = "mangaapp-ad-filter-style";
  const blockedHosts = [
    "doubleclick.net", "googlesyndication.com", "googleadservices.com",
    "adservice.google.com", "taboola.com", "outbrain.com", "adnxs.com",
    "adsrvr.org", "pubmatic.com", "flashtalking.com"
  ];
  const selectors = [
    "ins.adsbygoogle",
    "[id^='google_ads']",
    "[id^='div-gpt-ad']",
    "[class*='adsbygoogle']",
    "[class*='ad-container']",
    "[id*='ad-container']",
    "[class*='advertisement']",
    "[id*='advertisement']",
    "[class*='popunder']",
    "[class*='popup-ad']",
    "[id*='popup-ad']",
    "[class*='sponsor-banner']",
    "iframe[src*='doubleclick.net']",
    "iframe[src*='googlesyndication.com']",
    "iframe[src*='googleadservices.com']",
    "iframe[src*='taboola.com']",
    "iframe[src*='outbrain.com']"
  ];
  const state = window.__mangaAppAdFilterState ||
    (window.__mangaAppAdFilterState = { enabled: true, observer: null });
  if (!window.__mangaAppOriginalOpen) {
    window.__mangaAppOriginalOpen = window.open.bind(window);
    window.open = function(url, ...args) {
      if (state.enabled && url) {
        try {
          const host = new URL(String(url), location.href).hostname.toLowerCase();
          if (blockedHosts.some(domain => host === domain || host.endsWith("." + domain))) {
            return null;
          }
        } catch (_) {}
      }
      return window.__mangaAppOriginalOpen(url, ...args);
    };
  }
  if (!window.__mangaAppAdClickListenerInstalled) {
    document.addEventListener("click", event => {
      if (!state.enabled) return;
      const link = event.target && event.target.closest
        ? event.target.closest("a[href]") : null;
      if (!link) return;
      try {
        const host = new URL(link.href, location.href).hostname.toLowerCase();
        if (blockedHosts.some(domain => host === domain || host.endsWith("." + domain))) {
          event.preventDefault();
          event.stopImmediatePropagation();
        }
      } catch (_) {}
    }, true);
    window.__mangaAppAdClickListenerInstalled = true;
  }
  let style = document.getElementById(styleId);
  if (!style) {
    style = document.createElement("style");
    style.id = styleId;
    (document.head || document.documentElement).appendChild(style);
  }
  style.textContent = selectors.join(",") +
    "{display:none!important;visibility:hidden!important;max-height:0!important;min-height:0!important;pointer-events:none!important}";
  const apply = () => {
    if (!state.enabled) return;
    document.querySelectorAll(selectors.join(",")).forEach(el => {
      el.setAttribute("data-mangaapp-hidden-ad", "1");
    });
  };
  apply();
  if (!state.observer) {
    state.observer = new MutationObserver(apply);
    state.observer.observe(document.documentElement, { childList: true, subtree: true });
  }
  state.setEnabled = enabled => {
    state.enabled = Boolean(enabled);
    if (style) style.disabled = !state.enabled;
    if (state.enabled) apply();
  };
  state.setEnabled(true);
})();"""

DISABLE_AD_FILTER_JS = r"""(() => {
  const state = window.__mangaAppAdFilterState;
  if (state && state.setEnabled) state.setEnabled(false);
})();"""

IMAGE_EXTRACTION_JS = r"""(async () => {
  const prefix = "MANGAAPP_IMAGE_LIST:";
  const wait = ms => new Promise(resolve => setTimeout(resolve, ms));
  await wait(650);
  const adPattern = /(^|[\s_-])(ad|ads|advert|advertisement|sponsor|popunder|popup-ad)([\s_-]|$)/i;
  const urls = [];
  const seen = new Set();
  for (const img of Array.from(document.images || [])) {
    try {
      const parentText = [];
      let parent = img;
      for (let i = 0; parent && i < 5; i++, parent = parent.parentElement) {
        parentText.push(String(parent.id || "") + " " + String(parent.className || ""));
      }
      if (adPattern.test(parentText.join(" "))) continue;
      const raw = img.currentSrc || img.src ||
        img.getAttribute("data-src") ||
        img.getAttribute("data-original") ||
        img.getAttribute("data-lazy-src") ||
        img.getAttribute("data-url") || "";
      if (!raw) continue;
      const url = new URL(raw, location.href);
      if (!["http:", "https:"].includes(url.protocol)) continue;
      if (/doubleclick\.net|googlesyndication\.com|googleadservices\.com|taboola\.com|outbrain\.com/i.test(url.hostname)) continue;
      const width = Number(img.naturalWidth || img.width || img.getAttribute("width") || 0);
      const height = Number(img.naturalHeight || img.height || img.getAttribute("height") || 0);
      if (width && width < 180) continue;
      if (height && height < 240) continue;
      if (width && height && width * height < 60000) continue;
      if (seen.has(url.href)) continue;
      seen.add(url.href);
      urls.push(url.href);
      if (urls.length >= 180) break;
    } catch (_) {}
  }
  console.log(prefix + JSON.stringify(urls));
})();"""


def normalize_image_candidates(payload, base_url: str, limit: int = 180) -> list[str]:
    """Parse, resolve, validate, deduplicate and cap URLs extracted from page images."""
    if isinstance(payload, str):
        raw = payload.strip()
        if raw.startswith(IMAGE_MESSAGE_PREFIX):
            raw = raw[len(IMAGE_MESSAGE_PREFIX):]
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return []
    if not isinstance(payload, list):
        return []

    result: list[str] = []
    seen: set[str] = set()
    for entry in payload:
        if isinstance(entry, dict):
            raw_url = entry.get("url") or entry.get("src") or ""
            try:
                width = int(entry.get("width") or 0)
                height = int(entry.get("height") or 0)
            except (TypeError, ValueError):
                width = height = 0
            if width and width < 180:
                continue
            if height and height < 240:
                continue
            if width and height and width * height < 60000:
                continue
        elif isinstance(entry, str):
            raw_url = entry
        else:
            continue

        raw_url = str(raw_url or "").strip()
        if not raw_url:
            continue
        absolute = urljoin(base_url, raw_url)
        parsed = urlparse(absolute)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            continue
        if absolute in seen:
            continue
        seen.add(absolute)
        result.append(absolute)
        if len(result) >= max(1, min(int(limit), 250)):
            break
    return result
