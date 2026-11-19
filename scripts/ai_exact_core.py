# -*- coding: utf-8 -*-
"""Pure matching of exact film/series titles. Never collapse an identical film and TV show."""
from ai_art_core import normalize, year_of, tmdb_art, catalogue_art, rating_of


def candidate(query, record, kind, source):
    if not isinstance(record, dict) or kind not in ("film", "serie"):
        return None
    item = record.get("show") if source == "tvmaze" else record
    if not isinstance(item, dict):
        return None
    names = [item.get(k) for k in
             ("title", "name", "original_title", "original_name", "sorttitle")]
    requested = normalize(query)
    if not requested or requested not in {normalize(v) for v in names if v}:
        return None
    title = str(item.get("title") or item.get("name") or requested).strip()
    if source == "tmdb":
        art = tmdb_art(item)
    elif source in ("cinemeta", "tvmaze"):
        art = catalogue_art(item, source)
    elif source == "kodi":
        artwork = item.get("art") or {}
        art = {"poster": artwork.get("poster") or artwork.get("thumb") or "",
               "backdrop": artwork.get("fanart") or "",
               "year": year_of(item), "rating": rating_of(item)}
    else:
        return None
    return {"title": title, "kind": kind,
            "year": str(art.get("year") or ""),
            "poster": art.get("poster") or "",
            "backdrop": art.get("backdrop") or "",
            "rating": art.get("rating") or "",
            "_source": source}


def merge_candidates(rows, limit=16):
    """Deduplicate provider mirrors, but retain all distinct years and media types."""
    merged = {}
    priority = {"kodi": 4, "tmdb": 3, "cinemeta": 2, "tvmaze": 1}
    for row in rows:
        if not isinstance(row, dict):
            continue
        title, kind, year = row.get("title"), row.get("kind"), row.get("year")
        if not title or kind not in ("film", "serie"):
            continue
        key = (normalize(title), kind, str(year or ""))
        if key not in merged:
            merged[key] = dict(row)
        else:
            existing = merged[key]
            prefer_new = priority.get(row.get("_source"), 0) > priority.get(existing.get("_source"), 0)
            primary, other = (row, existing) if prefer_new else (existing, row)
            combined = dict(primary)
            for field in ("poster", "backdrop", "rating"):
                if not combined.get(field) and other.get(field):
                    combined[field] = other[field]
            merged[key] = combined
    def ranking(row):
        try:
            rating = float(row.get("rating") or 0)
        except (TypeError, ValueError):
            rating = 0
        # Series and high-rated popular exact matches appear first, but both
        # series and films remain visible and selectable.
        return (-rating, 0 if row["kind"] == "serie" else 1,
                -int(row["year"]) if str(row["year"]).isdigit() else 0,
                -priority.get(row.get("_source"), 0))
    return sorted(merged.values(), key=ranking)[:limit]
