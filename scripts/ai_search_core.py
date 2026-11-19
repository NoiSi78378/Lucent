# -*- coding: utf-8 -*-
"""Pure helpers for Lucent AI Search. No Kodi imports: regression-testable offline.

Stream4Me addon/master specials/search.py:new_search accepts item.search_text and
mode=all; launcher.makeItem accepts legacy query parameters after '?'.
"""
import json
import re
import unicodedata
from urllib.parse import quote

S4ME_ADDON = "plugin.video.s4me"
S4ME_PREFIX = "plugin://plugin.video.s4me/?channel=search&action=new_search&mode=all&search_text="

def stream4me_url(title):
    """Build the proven, prompt-free Stream4Me global search request."""
    value = (title or "").strip()
    if not value or len(value) > 160:
        raise ValueError("empty/oversized search title")
    return S4ME_PREFIX + quote(value, safe="")

def _clean(value, size=160):
    return re.sub(r"[\x00-\x1f\x7f]", " ", str(value or "")).strip()[:size]

def parse_ai(content):
    """Extract structured recommendations; model text/URLs are NEVER Kodi commands."""
    if isinstance(content, list):
        content = "".join(str(c.get("text", "")) for c in content if isinstance(c, dict))
    if not isinstance(content, str):
        raise ValueError("invalid model response")
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^\x60{3}(?:json)?\s*", "", text, flags=re.I)
        text = re.sub(r"\s*\x60{3}$", "", text)
    try:
        raw = json.loads(text)
    except (TypeError, ValueError):
        start, end = text.find("{"), text.rfind("}")
        if start < 0 or end < start:
            raise ValueError("AI returned no JSON object")
        raw = json.loads(text[start:end + 1])
    if not isinstance(raw, dict):
        raise ValueError("AI returned an invalid JSON shape")
    candidates = raw.get("titles") or []
    if not isinstance(candidates, list):
        candidates = []
    result, seen = [], set()
    for entry in candidates:
        if isinstance(entry, str):
            entry = {"title": entry}
        if not isinstance(entry, dict):
            continue
        title = _clean(entry.get("title"), 110)
        if not title or title.lower() in seen:
            continue
        seen.add(title.lower())
        reason = _clean(entry.get("reason"), 195)
        year = re.sub(r"[^0-9]", "", str(entry.get("year") or ""))[:4]
        kind = "serie" if str(entry.get("type") or "").lower() in ("tvshow", "series", "serie") else "film"
        result.append({"title": title, "reason": reason, "year": year, "kind": kind})
        if len(result) >= 5:
            break
    if not result:
        query = _clean(raw.get("query"), 110)
        if query:
            result = [{"title": query, "reason": "", "year": "", "kind": "film"}]
    return result, _clean(raw.get("message"), 250)

def normalize_title(title):
    value = unicodedata.normalize("NFKD", str(title or ""))
    value = "".join(c for c in value if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()

def matches_live(search_title, epg_title):
    """Avoid false live broadcasts for generic prompts and short words."""
    a, b = normalize_title(search_title), normalize_title(epg_title)
    if len(a) < 5 or len(b) < 5:
        return False
    return a == b or (len(a) >= 9 and (" " + a + " ") in (" " + b + " "))

def is_default_search(icon, action):
    return icon == "icons/search.png" and (
        action == "VideoLibrary.Search" or
        action == "ActivateWindow(Videos,plugin://plugin.video.lucent/?action=searchmenu,return)"
    )
