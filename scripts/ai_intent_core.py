# -*- coding: utf-8 -*-
"""Italian search-intent rules and strict, verified genre matching (no Kodi dependency)."""
import datetime
import re
import unicodedata

# TMDb movie/TV genre IDs, Cinemeta manifest options, and common Italian aliases.
# A requested genre is a hard constraint, never an AI-generated label.
GENRES = {
    "action": {"movie": 28, "tv": 10759, "catalog": "Action",
               "labels": ("action", "azione", "action adventure", "action & adventure"),
               "patterns": (r"\baction\b", r"\bazion[ei]\b", r"\badrenalin\w*")},
    "horror": {"movie": 27, "tv": None, "catalog": "Horror",
               "labels": ("horror", "orrore"),
               "patterns": (r"\bhorror\b", r"\borror\w*\b", r"\bspavent\w*\b")},
    "romance": {"movie": 10749, "tv": None, "catalog": "Romance",
                "labels": ("romance", "romantic", "romantico", "romantica", "sentimentale"),
                "patterns": (r"\bromantic\w*\b", r"\bsentimental\w*\b",
                             r"\bromance\b", r"\bd['’]?amore\b")},
    "comedy": {"movie": 35, "tv": 35, "catalog": "Comedy",
               "labels": ("comedy", "commedia", "comico", "comica"),
               "patterns": (r"\bcommedi\w*\b", r"\bcomic\w*\b", r"\bcomedy\b")},
    "thriller": {"movie": 53, "tv": None, "catalog": "Thriller",
                 "labels": ("thriller",),
                 "patterns": (r"\bthriller\b", r"\bsuspense\b")},
    "mystery": {"movie": 9648, "tv": 9648, "catalog": "Mystery",
                "labels": ("mystery", "mistero", "giallo"),
                "patterns": (r"\bmystery\b", r"\bmister\w*\b", r"\bgiall[io]\b")},
    "science_fiction": {"movie": 878, "tv": 10765, "catalog": "Sci-Fi",
                        "labels": ("science fiction", "sci fi", "sci-fi", "fantascienza", "sci fi fantasy"),
                        "patterns": (r"\bfantascien\w*\b", r"\bsci[\s-]?fi\b", r"\bscience fiction\b")},
    "fantasy": {"movie": 14, "tv": 10765, "catalog": "Fantasy",
                "labels": ("fantasy", "sci fi fantasy", "sci fi & fantasy"),
                "patterns": (r"\bfantasy\b", r"\bfantastic\w*\b")},
    "animation": {"movie": 16, "tv": 16, "catalog": "Animation",
                  "labels": ("animation", "animazione", "animato", "animata", "anime"),
                  "patterns": (r"\banimazion\w*\b", r"\banimat\w*\b", r"\banime\b")},
    "crime": {"movie": 80, "tv": 80, "catalog": "Crime",
              "labels": ("crime", "criminale", "poliziesco", "poliziesca"),
              "patterns": (r"\bcrime\b", r"\bcriminal\w*\b", r"\bpoliziesc\w*\b")},
    "drama": {"movie": 18, "tv": 18, "catalog": "Drama",
              "labels": ("drama", "drammatico", "drammatica", "drammatici"),
              "patterns": (r"\bdrammatic\w*\b", r"\bdrama\b")},
    "adventure": {"movie": 12, "tv": 10759, "catalog": "Adventure",
                  "labels": ("adventure", "avventura", "action adventure", "action & adventure"),
                  "patterns": (r"\bavventur\w*\b", r"\badventure\b")},
    "documentary": {"movie": 99, "tv": 99, "catalog": "Documentary",
                    "labels": ("documentary", "documentario"),
                    "patterns": (r"\bdocumentari\w*\b", r"\bdocumentary\b")},
    "western": {"movie": 37, "tv": 37, "catalog": "Western",
                "labels": ("western",), "patterns": (r"\bwestern\b",)},
    "war": {"movie": 10752, "tv": 10768, "catalog": "War",
            "labels": ("war", "guerra", "war politics", "war & politics"),
            "patterns": (r"\bd[i]? guerra\b", r"\bbellic\w*\b", r"\bwar\b")},
}

GENRE_IT = {"action": "azione", "horror": "horror", "romance": "romantici",
            "comedy": "commedia", "thriller": "thriller", "mystery": "mistero",
            "science_fiction": "fantascienza", "fantasy": "fantasy",
            "animation": "animazione", "crime": "crime", "drama": "drammatici",
            "adventure": "avventura", "documentary": "documentari",
            "western": "western", "war": "guerra"}


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
    elif re.search(r"\banno scorso\b|\bl['’]?anno passato\b|\bdell['’]?anno scorso\b", query):
        year = today.year - 1
    else:
        explicit = re.search(r"\b((?:19|20)\d{2})\b", query)
        if explicit:
            year = int(explicit.group(1))
    kind = ("serie" if re.search(r"\bserie\b|\bserial\b|\btv show\b|\btelefilm\b", query)
            else "film" if re.search(r"\bfilm\b|\bmovie\b|\bpellicol", query)
            else None)
    genre = None
    # Order matters: in "commedia romantica" a romance filter is more specific
    # than a broad comedy filter; other genre patterns are kept independent.
    for candidate in ("romance",) + tuple(g for g in GENRES if g != "romance"):
        if any(re.search(pattern, query) for pattern in GENRES[candidate]["patterns"]):
            genre = candidate
            break
    requests = re.search(
        r"\b(voglio|vorrei|cercami|consigliami|consiglia|suggerisci|"
        r"vedere|mostrami|trova|simile|simili|come|tipo|quali|"
        r"uscito|usciti|uscita|nuovo|nuovi|recente|recenti|"
        r"film|serie|quest['’]?anno|anno|del|nel)\b", query)
    words = query.split()
    direct = bool(1 <= len(words) <= 7 and not requests and not genre and
                  not re.search(r"\d{4}", query))
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
    """A genre needs POSITIVE evidence from Kodi, TMDb or Cinemeta/TVmaze.

    Unknown/missing metadata is not proof. For existing TMDb genre IDs, do
    not let a contradictory name or the LLM override the numeric metadata.
    """
    requested = intent.get("genre")
    if not requested:
        return True
    definition = GENRES.get(requested)
    if not definition:
        return False
    ids = row.get("genre_ids") or []
    if isinstance(ids, (list, tuple)) and ids:
        expected = definition["tv"] if row.get("kind") == "serie" else definition["movie"]
        return expected is not None and str(expected) in {str(g) for g in ids}
    labels = row.get("genres") or []
    if isinstance(labels, str):
        labels = re.split(r"[,|;/]", labels)
    if not isinstance(labels, (list, tuple)):
        return False
    aliases = {re.sub(r"[^a-z0-9]+", " ", _text(name)).strip()
               for name in definition["labels"]}
    for label in labels:
        norm = re.sub(r"[^a-z0-9]+", " ", _text(label)).strip()
        if norm in aliases:
            return True
    return False
