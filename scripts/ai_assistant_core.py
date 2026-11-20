# -*- coding: utf-8 -*-
"""Validated intent contract shared by all Lucent AI tools. No Kodi dependency."""
import datetime
import json
import re
from ai_art_core import normalize
from ai_intent_core import GENRES

GENRES = dict(GENRES)
GENRES.update({
    "history":{"movie":36,"tv":None}, "music":{"movie":10402,"tv":None},
    "family":{"movie":10751,"tv":10751}, "biography":{"movie":None,"tv":None},
})
OPS = ("search","answer","resume","play","library","add","epg","scan","unsupported")
FIELDS = {
    "operation": {"type":"string","enum":list(OPS)},
    "title":{"type":"string"}, "kind":{"type":"string","enum":["","film","serie"]},
    "year_from":{"type":"integer"}, "year_to":{"type":"integer"},
    "genres":{"type":"array","items":{"type":"string"}},
    "exclude_genres":{"type":"array","items":{"type":"string"}},
    "people":{"type":"array","items":{"type":"object","properties":{
        "name":{"type":"string"},"role":{"type":"string","enum":["actor","director","writer","composer"]},
        "exclude":{"type":"boolean"}},"required":["name","role","exclude"],"additionalProperties":False}},
    "countries":{"type":"array","items":{"type":"string"}},
    "exclude_countries":{"type":"array","items":{"type":"string"}},
    "language":{"type":"string"}, "runtime_min":{"type":"integer"},"runtime_max":{"type":"integer"},
    "rating_min":{"type":"number"},"votes_min":{"type":"integer"},
    "seasons_min":{"type":"integer"},"seasons_max":{"type":"integer"},
    "status":{"type":"string","enum":["","ended","ongoing","canceled"]},
    "released":{"type":"boolean"}, "unwatched":{"type":"boolean"},
    "exclude_titles":{"type":"array","items":{"type":"string"}},
    "similar":{"type":"array","items":{"type":"string"}},
    "themes":{"type":"array","items":{"type":"string"}},
    "candidates":{"type":"array","items":{"type":"string"}},
    "unverified":{"type":"array","items":{"type":"string"}},
    "season":{"type":"integer"},"episode":{"type":"integer"},
    "provider":{"type":"string"},"question":{"type":"string"},
    "order":{"type":"string","enum":["relevance","recent","oldest","rating","popular"]},
    "followup":{"type":"boolean"}
}
SCHEMA = {"type":"object","properties":FIELDS,"required":list(FIELDS),"additionalProperties":False}


def clean(value, length=180):
    if not isinstance(value,str):
        return ""
    return re.sub(r"[\x00-\x1f\x7f]"," ",value).strip()[:length]


def number(value,maximum=2200):
    if isinstance(value,bool) or not isinstance(value,(int,float)):
        return 0
    if not 0 <= value <= maximum:
        return 0
    return int(value)


def validate(raw):
    """Never pass an unvalidated model parameter to a network or mutation tool."""
    if not isinstance(raw,dict) or raw.get("operation") not in OPS:
        raise ValueError("Piano AI non valido")
    p={}
    for key,spec in FIELDS.items():
        value=raw.get(key)
        typ=spec["type"]
        if typ=="string":
            p[key]=clean(value,500 if key=="question" else 180)
            if "enum" in spec and p[key] not in spec["enum"]:
                p[key]=spec["enum"][0]
        elif typ=="boolean":
            p[key]=value is True
        elif typ=="integer":
            p[key]=number(value,1000000 if key=="votes_min" else 2200)
        elif typ=="number":
            p[key]=float(value) if isinstance(value,(int,float)) and not isinstance(value,bool) and 0<=value<=10 else 0
        elif typ=="array":
            values=value[:20] if isinstance(value,list) else []
            if key=="people":
                p[key]=[{"name":clean(x.get("name")),"role":x["role"],"exclude":x.get("exclude") is True}
                        for x in values if isinstance(x,dict) and clean(x.get("name")) and
                        x.get("role") in ("actor","director","writer","composer")][:6]
            else:
                p[key]=list(dict.fromkeys(clean(x) for x in values if clean(x)))
    for key in ("genres","exclude_genres"):
        p[key]=[x.casefold() for x in p[key]]
        unknown=[x for x in p[key] if x not in GENRES]
        p["unverified"]+=unknown
        p[key]=[x for x in p[key] if x in GENRES]
    for key in ("countries","exclude_countries"):
        invalid=[x for x in p[key] if not re.fullmatch(r"[A-Za-z]{2}",x)]
        p["unverified"]+=invalid
        p[key]=[x.upper() for x in p[key] if re.fullmatch(r"[A-Za-z]{2}",x)]
    if p["language"] and not re.fullmatch(r"[a-z]{2}",p["language"]):
        p["unverified"].append("lingua "+p["language"])
        p["language"]=""
    for lo,hi in (("year_from","year_to"),("runtime_min","runtime_max"),("seasons_min","seasons_max")):
        if p[lo] and p[hi] and p[lo]>p[hi]:
            raise ValueError("Intervallo non valido: "+lo)
    return p


def hard_filters(p):
    return any(p.get(k) for k in ("year_from","year_to","genres","exclude_genres",
        "people","countries","exclude_countries","language","runtime_min","runtime_max",
        "rating_min","votes_min","seasons_min","seasons_max","status","released",
        "unwatched","exclude_titles","unverified","season","episode"))


def matches(item,p,kind,today=None):
    """Check detail evidence, not model text. Return false for missing hard evidence."""
    today=today or datetime.date.today().isoformat()
    date=str(item.get("release_date") if kind=="film" else item.get("first_air_date") or "")
    title=item.get("title") or item.get("name") or ""
    if not title or (p["kind"] and p["kind"]!=kind):
        return False
    if normalize(title) in {normalize(x) for x in p["exclude_titles"]}:
        return False
    if p["year_from"] or p["year_to"] or p["released"]:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}",date):
            return False
        year=int(date[:4])
        if p["year_from"] and year<p["year_from"] or p["year_to"] and year>p["year_to"]:
            return False
        if p["released"] and date>today:
            return False
    ids={x.get("id") for x in item.get("genres",[]) if isinstance(x,dict)}
    ids.update(item.get("genre_ids") or [])
    for key in ("genres","exclude_genres"):
        for genre in p[key]:
            gid=GENRES[genre]["movie" if kind=="film" else "tv"]
            if gid is None or not ids or (key=="genres" and gid not in ids) or (key=="exclude_genres" and gid in ids):
                return False
    countries={x.get("iso_3166_1") for x in item.get("production_countries",[]) if isinstance(x,dict)}
    countries.update(item.get("origin_country") or [])
    if p["countries"] and not set(p["countries"]).issubset(countries):
        return False
    if p["exclude_countries"] and (not countries or countries.intersection(p["exclude_countries"])):
        return False
    if p["language"] and item.get("original_language")!=p["language"]:
        return False
    rt=item.get("runtime") if kind=="film" else item.get("episode_run_time")
    runtimes=[rt] if isinstance(rt,(int,float)) else rt or []
    if p["runtime_min"] or p["runtime_max"]:
        if not runtimes or any(not isinstance(x,(int,float)) or x<=0 or
              (p["runtime_min"] and x<p["runtime_min"]) or (p["runtime_max"] and x>p["runtime_max"])
              for x in runtimes):
            return False
    for field,lower,upper in (("vote_average","rating_min",None),("vote_count","votes_min",None),
                              ("number_of_seasons","seasons_min","seasons_max")):
        val=item.get(field)
        lo=p.get(lower,0); hi=p.get(upper,0) if upper else 0
        if (lo or hi) and (not isinstance(val,(int,float)) or (lo and val<lo) or (hi and val>hi)):
            return False
    if p["status"]:
        status=str(item.get("status") or "").casefold()
        if status not in {"ended":{"ended"},"ongoing":{"returning series","in production"},
                          "canceled":{"canceled"}}[p["status"]]:
            return False
    credits=item.get("credits")
    for person in p["people"]:
        if not isinstance(credits,dict):
            return False
        role=person["role"]
        rows=credits.get("cast" if role=="actor" else "crew")
        if not isinstance(rows,list):
            return False
        jobs={"director":{"director"},"writer":{"writer","screenplay","story"},
              "composer":{"original music composer","music","composer"}}
        found=any(isinstance(x,dict) and normalize(x.get("name"))==normalize(person["name"]) and
                  (role=="actor" or str(x.get("job") or "").casefold() in jobs[role]) for x in rows)
        if found==person["exclude"]:
            return False
    return True


def choose_episode(episodes,watched=(),requested=None):
    """Preserve partial progress; never pick an already completed episode by default."""
    known=set(tuple(x) for x in watched)
    usable=[x for x in episodes if x.get("episodeid") and isinstance(x.get("season"),int)
            and x["season"]>0 and isinstance(x.get("episode"),int) and x["episode"]>0]
    usable.sort(key=lambda x:(x["season"],x["episode"]))
    if requested:
        return next((x for x in usable if (x["season"],x["episode"])==tuple(requested)),None)
    remaining=[x for x in usable if not x.get("playcount") and
               (x["season"],x["episode"]) not in known]
    partial=[x for x in remaining if (x.get("resume") or {}).get("position",0)>0]
    return max(partial,key=lambda x:x.get("lastplayed") or "") if partial else next(iter(remaining),None)
