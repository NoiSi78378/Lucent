# -*- coding: utf-8 -*-
"""Verified person-intent and cast/crew credit handling, with no Kodi dependency.

An AI suggestion MUST NOT substitute for actual cast/crew credits. These
functions only accept an exact person match and explicit TMDb credit records.
"""
import re
import unicodedata
from ai_art_core import normalize, tmdb_art
from ai_intent_core import genre_eligible


def person_intent(query):
    """Italian 'film con Robert Pattinson' / 'diretto da Nolan' queries."""
    q = str(query or "").strip()
    markers = [
        (r"\b(?:dirett[oa] da|regia di|regista\s+)\s+", "director"),
        (r"\b(?:interpretat[oa] da|con l['’]attor[ea]\s+|"
         r"con l['’]attrice\s+|con\s+)\s*", "actor"),
    ]
    for marker, role in markers:
        found = re.search(marker, q, flags=re.IGNORECASE)
        if not found:
            continue
        remainder = q[found.end():]
        remainder = re.split(
            r"\s+(?:del|nel|uscit[oaie]|dell['’]anno|quest['’]anno|"
            r"di\s+quest['’]anno|che\s+|e\s+un\s+film\b|per\s+favore)\b",
            remainder, maxsplit=1, flags=re.IGNORECASE)[0]
        remainder = re.sub(r"\s+(?:del|nel)\s*$", "", remainder, flags=re.IGNORECASE)
        name = remainder.strip(" \t.,:;!?\"“”")
        # Avoid treating a bare genre or a complete sentence as a person name.
        words = name.split()
        if 2 <= len(words) <= 5 and all(
                re.fullmatch(r"[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ'’.-]*", word) for word in words):
            return {"name": name, "role": role}
    return None


def find_person(results, full_name, role="actor"):
    exact = normalize(full_name)
    if not exact:
        return None
    valid = []
    for item in results if isinstance(results, list) else []:
        if not isinstance(item, dict):
            continue
        names = [item.get("name")] + list(item.get("also_known_as") or [])
        if exact not in {normalize(n) for n in names if n}:
            continue
        if role == "actor" and item.get("known_for_department") not in (
                None, "Acting"):
            continue
        valid.append(item)
    return max(valid, key=lambda x: float(x.get("popularity") or 0)) if valid else None


def credit_rows(credits, media, role, intent):
    """Credit endpoints are authoritative for participation in the film/show."""
    if media not in ("film", "serie"):
        return []
    key = "cast" if role == "actor" else "crew"
    rows = []
    for item in credits.get(key) or [] if isinstance(credits, dict) else []:
        if not isinstance(item, dict):
            continue
        if role == "director" and item.get("job") != "Director":
            continue
        art = tmdb_art(item)
        year = str(art.get("year") or "")
        if intent.get("year") and year != str(intent["year"]):
            continue
        if intent.get("released") and str(
                item.get("release_date") or item.get("first_air_date") or ""
                )[:10] > intent.get("today", ""):
            continue
        row = {
            "title": str(item.get("title") or item.get("name") or "").strip(),
            "kind": media, "year": year, "verified_year": year,
            "poster": art.get("poster") or "",
            "backdrop": art.get("backdrop") or "",
            "rating": art.get("rating") or "",
            "genre_ids": item.get("genre_ids") or [],
            "reason": "Presenza verificata nei crediti TMDb",
        }
        if row["title"] and genre_eligible(row, intent):
            rows.append(row)
    rows.sort(key=lambda row: (
        -(float(row["rating"]) if row["rating"] else 0),
        -int(row["year"]) if row["year"].isdigit() else 0,
        row["title"]))
    seen = set()
    results = []
    for row in rows:
        key = (normalize(row["title"]), row["kind"], row["year"])
        if key not in seen:
            seen.add(key)
            results.append(row)
    return results
