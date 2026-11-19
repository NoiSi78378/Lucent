# -*- coding: utf-8 -*-
"""Pure Italian search-intent rules, separate from Kodi and free-model guesses."""
import datetime
import re
import unicodedata


def _text(value):
    text = unicodedata.normalize("NFKD", str(value or "").casefold())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", text).strip()


def understand(prompt, today=None):
    today = today or datetime.date.today()
    query = _text(prompt)
    year = None
    if re.search(r"\bquest['’]?anno\b|\banno corrente\b|\bquesto anno\b", query):
        year = today.year
    elif re.search(r"\banno scorso\b|\bl['’]?anno passato\b", query):
        year = today.year - 1
    else:
        explicit = re.search(r"\b((?:19|20)\d{2})\b", query)
        if explicit:
            year = int(explicit.group(1))
    kind = ("serie" if re.search(r"\bserie\b|\bserial\b|\btv show\b|\btelefilm\b", query)
            else "film" if re.search(r"\bfilm\b|\bmovie\b|\bpellicol", query)
            else None)
    genre = "action" if re.search(r"\baction\b|\bazione\b|\badrenalin", query) else None
    # Only plain title phrases use the exact-title path. Requests, comparisons and
    # recommendations must still use the AI (e.g. "serie come Silo").
    requests = re.search(
        r"\b(voglio|vorrei|cercami|consigliami|consiglia|suggerisci|"
        r"vedere|mostrami|trova|simile|simili|come|tipo|quali|"
        r"uscito|usciti|uscita|nuovo|nuovi|recente|recenti|"
        r"action|azione|film|serie|horror|commedia|thriller|"
        r"quest['’]?anno|anno|del|nel)\b", query)
    words = query.split()
    direct = bool(1 <= len(words) <= 7 and not requests and not re.search(r"\d{4}", query))
    return {"direct": direct, "year": year, "kind": kind, "genre": genre,
            "released": bool(re.search(r"\buscit[oiae]\b|\bgi[aà] uscit", query)),
            "today": today.isoformat()}


def year_eligible(row, intent):
    """A requested year requires a year from a matched metadata source."""
    year = intent.get("year")
    if not year:
        return True
    return str(row.get("verified_year") or "") == str(year)


def genre_eligible(row, intent):
    """Only reject known contradictory genres; unknown genres are not verified."""
    if intent.get("genre") != "action":
        return True
    ids = row.get("genre_ids") or []
    labels = row.get("genres") or []
    if ids:
        return 28 in ids or "28" in ids
    if labels:
        return any("action" in str(x).casefold() or "azione" in str(x).casefold()
                   for x in labels)
    return True
