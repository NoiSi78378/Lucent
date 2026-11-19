# -*- coding: utf-8 -*-
"""Pure, offline-testable artwork matching for Lucent AI Search."""
import re
import unicodedata


def normalize(value):
    value = unicodedata.normalize("NFKD", str(value or "").casefold())
    value = "".join(c for c in value if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def year_of(entry):
    for key in ("first_air_date", "release_date", "premiered", "year"):
        value = str(entry.get(key) or "")
        found = re.search(r"\b(?:19|20)\d{2}\b", value)
        if found:
            return found.group(0)
    return ""


def choose_record(records, title, year=""):
    """Match the actual title (including original title), not an approximate neighbour.

    Movie and TV catalogues are queried separately by caller. Year only breaks ties:
    the model can provide inaccurate years, so it must not discard an exact title.
    """
    wanted = normalize(title)
    if not wanted or not isinstance(records, list):
        return None
    matches = []
    for record in records[:35]:
        if not isinstance(record, dict):
            continue
        item = record.get("show") if isinstance(record.get("show"), dict) else record
        names = (item.get("title"), item.get("name"), item.get("original_title"),
                 item.get("original_name"))
        if wanted not in {normalize(name) for name in names if name}:
            continue
        found_year = year_of(item)
        diff = abs(int(found_year) - int(year)) if found_year and str(year).isdigit() else 0
        matches.append((diff, item))
    return min(matches, key=lambda pair: pair[0])[1] if matches else None


def safe_image(value):
    """Remote catalogue artwork must be HTTPS; local Kodi art is handled separately."""
    url = str(value or "").strip()
    if not url.startswith("https://") or re.search(r"[\x00-\x20<>'\"]", url):
        return ""
    return url[:800] if len(url) <= 800 else ""


def tmdb_art(item):
    if not isinstance(item, dict):
        return {}
    art = {}
    for source, target, size in (("poster_path", "poster", "w342"),
                                 ("backdrop_path", "backdrop", "w780")):
        path = item.get(source) or ""
        if re.fullmatch(r"/[A-Za-z0-9._/-]{4,180}", str(path)):
            art[target] = "https://image.tmdb.org/t/p/" + size + path
    art["year"] = year_of(item)
    art["rating"] = rating_of(item)
    return art


def rating_of(item):
    raw = item.get("vote_average")
    if raw is None:
        raw = item.get("imdbRating")
    if raw is None and isinstance(item.get("rating"), dict):
        raw = item["rating"].get("average")
    try:
        score = float(raw)
    except (TypeError, ValueError):
        return ""
    return ("%.1f" % score) if 0 < score <= 10 else ""


def catalogue_art(item, source):
    if not isinstance(item, dict):
        return {}
    if source == "tvmaze":
        image = item.get("image") or {}
        poster = (image.get("original") or image.get("medium")) if isinstance(image, dict) else ""
        backdrop = ""
    else:
        poster = item.get("poster")
        backdrop = item.get("background") or item.get("fanart")
    return {"poster": safe_image(poster), "backdrop": safe_image(backdrop),
            "year": year_of(item), "rating": rating_of(item)}



def backdrop_full(url):
    """High-resolution *landscape* art, distinct from small card thumbnails.

    TMDb serves the same backdrop asset at its native image resolution.
    MetaHub/Cinemeta's medium backgrounds can be requested in their large
    landscape rendition. Unknown image sources are never fabricated.
    """
    link = safe_image(url)
    if not link:
        return ""
    tmdb = re.fullmatch(
        r"https://image\.tmdb\.org/t/p/(?:w300|w780|w1280|original)"
        r"(/[A-Za-z0-9._/-]{4,180})", link)
    if tmdb:
        return "https://image.tmdb.org/t/p/original" + tmdb.group(1)
    meta = re.fullmatch(
        r"https://images\.metahub\.space/background/(?:small|medium|large|original)"
        r"/(tt\d{5,12})/img", link)
    if meta:
        return "https://images.metahub.space/background/large/" + meta.group(1) + "/img"
    return link


def metadata_label(row):
    kind = "IN DIRETTA" if row.get("kind") == "live" else (
        "SERIE TV" if row.get("kind") == "serie" else "FILM")
    parts = [kind]
    if row.get("year") and row.get("kind") != "live":
        parts.append(str(row["year"]))
    if row.get("rating") and row.get("kind") != "live":
        parts.append("★ " + str(row["rating"]))
    return "  ·  ".join(parts)
