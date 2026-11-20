# -*- coding: utf-8 -*-
"""PVR assistant: local channel identity, EPG and tuning. No external streams."""
import datetime as dt
import re
import unicodedata

def norm(value):
    s=unicodedata.normalize("NFKD",str(value or "").casefold())
    return "".join(x for x in s if x.isalnum() and not unicodedata.combining(x))

def channel_keys(name):
    key=norm(name)
    keys={key}
    # Strip common quality markers only from the end; preserve numbered channels.
    for suffix in ("fullhd","uhd","fhd","1080p","720p","4k","hd","sd"):
        if key.endswith(suffix) and len(key)>len(suffix):
            keys.add(key[:-len(suffix)])
    aliases={"raiuno":"rai1","raidue":"rai2","raitre":"rai3","canalecinque":"canale5",
             "italiauno":"italia1","retequattro":"rete4","la7d":"la7d"}
    return {aliases.get(k,k) for k in keys if k}

def match_channels(channels,name):
    target=channel_keys(name)
    hits=[c for c in channels if c.get("channelid") and
          target.intersection(channel_keys(c.get("channel") or c.get("label")))]
    hits.sort(key=lambda c:(norm(name)!=norm(c.get("channel") or c.get("label")),
                            "hd" not in norm(c.get("channel") or c.get("label")),
                            c.get("channelid")))
    return hits

def local_request(query,channels=()):
    """Only claim explicit TV syntax or an exact installed channel match."""
    q=str(query or "").strip().rstrip("?!., ")
    when="tonight" if re.search(r"\b(?:stasera|questa sera|in prima serata)\b",q,re.I) else (
        "tomorrow" if re.search(r"\bdomani\b",q,re.I) else (
        "today" if re.search(r"\boggi\b",q,re.I) else "now"))
    text=re.sub(r"\s+(?:stasera|questa sera|in prima serata|domani|oggi|adesso|ora)\s*$","",q,flags=re.I)
    verbs=r"(?:metti|sintonizz(?:a|ami)|passa|vai|apri|avvia|fammi vedere|voglio vedere|guarda)"
    m=re.fullmatch(verbs+r"\s+(?:(?:su|sul|sulla|al|alla|il|la)\s+)?(?:(?:canale|tv)\s+)?(.+)",text,re.I)
    if m:
        name=m.group(1).strip()
        if match_channels(channels,name) or re.search(r"\b(?:canale|tv in diretta)\b",text,re.I):
            return {"operation":"tune","channel":name,"when":"now"}
    m=re.fullmatch(r"(?:cosa\s+(?:c['’][eè]|danno|trasmettono|fanno|va in onda)|che\s+(?:cosa\s+)?(?:danno|trasmettono|fanno)|che\s+programma\s+c['’][eè])\s+(?:su|sul|sulla|in)\s+(.+)",text,re.I)
    if m:
        name=m.group(1).strip()
        if norm(name) in ("tv","televisione","diretta"):
            return {"operation":"epg","channel":"","when":when}
        if match_channels(channels,name) or re.match(r"(?i)(?:rai|italia\s*\d|d\s*max|canale|rete\s*\d|la\s*7)\b",name):
            return {"operation":"epg","channel":name,"when":when}
    return None

def channels(rpc):
    # Official alltv selector is stable even when group labels are localized.
    props=["channel","channelnumber","hidden","locked","broadcastnow","broadcastnext"]
    result=[]; seen=set()
    def fetch(group):
        start=0
        for _ in range(30):
            data=rpc("PVR.GetChannels",{"channelgroupid":group,"properties":props,
                                        "limits":{"start":start,"end":start+200}})
            rows=data.get("channels") or []
            for r in rows:
                if isinstance(r,dict) and r.get("channelid") and not r.get("hidden") and r["channelid"] not in seen:
                    seen.add(r["channelid"]);result.append(r)
            limits=data.get("limits") or {}
            end=limits.get("end",start+len(rows))
            if not rows or end<=start or end>=limits.get("total",end): break
            start=end
    try:
        fetch("alltv")
    except (RuntimeError,TypeError,ValueError):
        groups=rpc("PVR.GetChannelGroups",{"channeltype":"tv"}).get("channelgroups") or []
        for g in groups:
            if g.get("channelgroupid"):
                try: fetch(g["channelgroupid"])
                except (RuntimeError,TypeError,ValueError): continue
    return result

def date_value(value):
    # Kodi JSON-RPC time fields are UTC. Convert to the device's local time.
    try:
        x=dt.datetime.fromisoformat(str(value).replace("Z","+00:00"))
        if x.tzinfo is None: x=x.replace(tzinfo=dt.timezone.utc)
        return x.astimezone()
    except (ValueError,TypeError): return None

def label(c):
    return str(c.get("channel") or c.get("label") or "Canale")

def broadcast_title(b):
    return str(b.get("title") or b.get("label") or "").strip()

def line(b,c=None):
    title=broadcast_title(b)
    start=date_value(b.get("starttime")); end=date_value(b.get("endtime"))
    clock=(start.strftime("%H:%M")+"–"+end.strftime("%H:%M")+"  ") if start and end else ""
    return (label(c)+" · " if c else "")+clock+title

def schedule(rpc,channel,when,now=None):
    now=now or dt.datetime.now().astimezone()
    if when=="now":
        b=channel.get("broadcastnow")
        if isinstance(b,dict) and broadcast_title(b): return [b]
        return []
    if when=="next":
        b=channel.get("broadcastnext")
        if isinstance(b,dict) and broadcast_title(b): return [b]
        return []
    date=now.date()+dt.timedelta(days=1 if when=="tomorrow" else 0)
    low=dt.datetime.combine(date,dt.time(19 if when=="tonight" else 0)).astimezone()
    high=dt.datetime.combine(date+dt.timedelta(days=1),dt.time()).astimezone()
    if when=="today": low=max(low,now)
    out=[]; start=0
    for _ in range(20):
        data=rpc("PVR.GetBroadcasts",{"channelid":channel["channelid"],
            "properties":["title","starttime","endtime","genre","plot","originaltitle"],
            "limits":{"start":start,"end":start+200}})
        rows=data.get("broadcasts") or []
        for b in rows:
            a=date_value(b.get("starttime"));z=date_value(b.get("endtime"))
            if a and z and a<high and z>low and broadcast_title(b): out.append(b)
        limits=data.get("limits") or {}; end=limits.get("end",start+len(rows))
        if not rows or end<=start or end>=limits.get("total",end): break
        start=end
    return sorted(out,key=lambda b:b.get("starttime") or "")

def tune(rpc,channel):
    if channel.get("locked"): raise RuntimeError("Canale bloccato: aprilo dalla guida Kodi.")
    return rpc("Player.Open",{"item":{"channelid":int(channel["channelid"])}})
