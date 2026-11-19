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
    """Read JSON from heterogeneous free models, with safe title-list fallback."""
    if isinstance(content, list):
        content = "\n".join(
            str(item.get("text") or item.get("content") or "")
            for item in content if isinstance(item, dict)
        )
    if not isinstance(content, str) or not content.strip():
        raise ValueError("AI returned empty content")
    text = content.strip()
    cleaned = re.sub(r"^\s*\x60{3}(?:json)?\s*", "", text, flags=re.I)
    cleaned = re.sub(r"\s*\x60{3}\s*$", "", cleaned)
    raw = None
    try:
        raw = json.loads(cleaned)
    except (TypeError, ValueError):
        decoder = json.JSONDecoder()
        starts = sorted(index for index in (cleaned.find("{"), cleaned.find("["))
                        if index >= 0)
        for start in starts:
            try:
                raw, _ = decoder.raw_decode(cleaned[start:])
                break
            except ValueError:
                continue

    if isinstance(raw, list):
        raw = {"titles": raw}
    candidates = []
    message = ""
    if isinstance(raw, dict):
        message = _clean(raw.get("message") or raw.get("messaggio") or "", 250)
        for key in ("titles", "titoli", "recommendations", "suggestions", "results", "risultati"):
            value = raw.get(key)
            if isinstance(value, list) and value:
                candidates = value
                break
        if not candidates and (raw.get("title") or raw.get("titolo")):
            candidates = [raw]

    # Some free models ignore JSON instructions and return numbered suggestions.
    # Only parse explicitly enumerated/bulleted lines, not arbitrary prose or URLs.
    if not candidates:
        for line in text.splitlines():
            match = re.match(r"^\s*(?:[-*•]|\d{1,2}[.)])\s+(.+)$", line)
            if not match:
                continue
            value = match.group(1).strip()
            value = re.sub(r"^\*{1,2}(.*?)\*{1,2}(?:\s.*)?$", r"\1", value)
            value = re.split(r"\s+[–—-]\s+|:\s+", value, maxsplit=1)[0]
            value = re.sub(r"\s*\((?:19|20)\d{2}\)\s*$", "", value)
            value = _clean(value.strip(" \x60*_'\"“”«»"), 110)
            if 2 <= len(value) <= 90 and re.search(r"[A-Za-zÀ-ÿ]", value) \
                    and "http" not in value.lower():
                candidates.append({"title": value})
            if len(candidates) >= 5:
                break

    result, seen = [], set()
    for entry in candidates:
        if isinstance(entry, str):
            entry = {"title": entry}
        if not isinstance(entry, dict):
            continue
        title = _clean(entry.get("title") or entry.get("titolo") or entry.get("name"), 110)
        title = title.strip(" \x60")
        if not title or title.lower() in seen or title.lower().startswith(("http://", "https://")):
            continue
        seen.add(title.lower())
        reason = _clean(entry.get("reason") or entry.get("motivo") or entry.get("why"), 195)
        year = re.sub(r"[^0-9]", "", str(entry.get("year") or entry.get("anno") or ""))[:4]
        media_type = str(entry.get("type") or entry.get("media_type") or "").lower()
        kind = "serie" if media_type in ("tvshow", "tv", "tv_show", "series", "serie", "serie tv") else "film"
        result.append({"title": title, "reason": reason, "year": year, "kind": kind})
        if len(result) >= 8:
            break
    if not result and isinstance(raw, dict):
        query = _clean(raw.get("query") or raw.get("ricerca"), 110)
        if query:
            result = [{"title": query, "reason": "", "year": "", "kind": "film"}]
    return result, message


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
