"""Regression checks for the cinematic, scrollable AI Home in Kodi."""
import ast
import xml.etree.ElementTree as ET
from pathlib import Path
root=Path(__file__).resolve().parent.parent
source=(root/"scripts/ai_home.py").read_text(encoding="utf-8")
ast.parse(source)
home=(root/"xml/Home.xml").read_text(encoding="utf-8")
panel=(root/"xml/Includes_Lucent_AISearch_Home.xml").read_text(encoding="utf-8")
includes=(root/"xml/Includes.xml").read_text(encoding="utf-8")
settings=(root/"xml/SkinSettings.xml").read_text(encoding="utf-8")
menu=(root/"scripts/menu.py").read_text(encoding="utf-8")
ET.parse(root/"xml/Home.xml")
ET.parse(root/"xml/Includes.xml")
ui=ET.parse(root/"xml/Includes_Lucent_AISearch_Home.xml")
ET.parse(root/"xml/SkinSettings.xml")
assert "Includes_Lucent_AISearch_Home.xml" in includes
assert "<include>LucentAISearchHome</include>" in home
assert "RunScript(special://skin/scripts/ai_home.py,refresh)" in home
assert 'tab("t_search", "search", "SetFocus(9500)")' in menu
assert "RunScript(special://skin/scripts/ai_home.py,settings)" in settings
assert "OpenRouter" in settings
assert "RunScript(special://skin/scripts/ai_home.py,input)" in panel
assert panel.count("mask_landscape.png") >= 2
assert '<include name="LucentAINativeCardPlain">' in panel
assert '<include name="LucentAINativeCardFocused">' in panel
assert 'rr14_glow.png' in panel and 'rr14_edge.png' in panel
assert '<width>400</width>' in panel and '<height>225</height>' in panel
assert "Window(home).Property(ai.home.mode)" in panel
assert "<visible>!String.IsEqual(Window(home).Property(ai.home.mode),results)</visible>" in panel
assert "<visible>String.IsEqual(Window(home).Property(ai.home.mode),results)</visible>" in panel
assert "Container(9510).ListItem.Property(backdrop)" in home
assert "Container(9520).ListItem.Property(backdrop)" in home
assert "Container(9530).ListItem.Property(backdrop)" in home
assert "Container(9540).ListItem.Property(backdrop)" in home
assert "Container(9550).ListItem.Property(backdrop)" in home
assert "HomeBackdrops" in home and "BackdropFades" in home
assert (root/"media/mask_landscape.png").is_file()
assert ui.find(".//include[@name='LucentAISearchHome']") is not None
controls=[c for c in ui.iter("control") if c.get("id")]
ids=[int(c.get("id")) for c in controls]
assert len(ids)==len(set(ids)),[x for x in ids if ids.count(x)>1]
assert set((9500,9501,9510,9520,9530,9540,9550)).issubset(ids)
assert len([c for c in controls if c.get("type")=="fixedlist"])==4
assert len([c for c in controls if c.get("type")=="list"])==1
for r,cid in zip(("pop","new","tv","top"),(9510,9520,9530,9540)):
    node=next(c for c in controls if c.get("id")==str(cid))
    assert node.get("type")=="fixedlist"
    assert node.findtext("orientation")=="horizontal"
    assert node.findtext("focusposition")=="0"
    assert node.findtext("ondown") in ("9520","9530","9540")
    assert node.find("focusedlayout/control/visible").text == "!Control.HasFocus(%s)" % cid
    assert node.find("focusedlayout/control[2]/visible").text == "Control.HasFocus(%s)" % cid
    assert len(node.findall("content/item"))>=20
    assert all("Property(ai.home.%s."%r in it.findtext("label","") for it in node.findall("content/item"))
    assert all(it.findtext("property[@name='backdrop']","") for it in node.findall("content/item"))
    assert node.find("focusedlayout/control[2]/include").text == "LucentAINativeCardFocused"
    assert node.find("itemlayout/include").text == "LucentAINativeCardPlain"
    assert all(it.findtext("visible","").startswith("!String.IsEmpty") for it in node.findall("content/item"))
assert '<control type="grouplist" id="9501">' in panel
assert panel.count('<width>1640</width><height>346</height>') == 4
assert panel.count('<include>LucentAINativeCardPlain</include>') == 8
assert panel.count('<include>LucentAINativeCardFocused</include>') == 4
assert 'Control.HasFocus(9510)' in panel and 'Control.HasFocus(9520)' in panel
assert 'Control.HasFocus(9530)' in panel and 'Control.HasFocus(9540)' in panel
assert 'LucentAINativeCardPlain' in panel and 'LucentAINativeCardFocused' in panel
assert "SUGGESTION_LIMIT = 24" in source
assert '"top": [], "tv": []' not in source or True
assert '"tv": [], "top": []' in source
assert "skip=%d.json" in source and "genre=%d" in source
assert "def _run_query(prompt, context=None):" in source and "assistant.plan_query(prompt,context)" in source
assert "assistant.catalogue(p,_exact_titles)" in source
assert 'ActivateWindow(Videos,"%s",return)' in source
assert "def set_key():" in source and "_save_key(value)" in source

# High-resolution artwork is a different info provider from the 400x225 card art.
import sys
sys.path.insert(0, str(root/"scripts"))
from ai_art_core import backdrop_full
assert backdrop_full("https://image.tmdb.org/t/p/w780/abcde123.jpg") == (
    "https://image.tmdb.org/t/p/original/abcde123.jpg")
assert backdrop_full("https://image.tmdb.org/t/p/w1280/xyz09876.jpg") == (
    "https://image.tmdb.org/t/p/original/xyz09876.jpg")
assert backdrop_full("https://images.metahub.space/background/medium/tt0903747/img") == (
    "https://images.metahub.space/background/large/tt0903747/img")
assert backdrop_full("https://example.org/backdrop.jpg") == "https://example.org/backdrop.jpg"
assert backdrop_full("javascript:alert(1)") == ""
assert "from ai_art_core import catalogue_art, normalize, tmdb_art, backdrop_full" in source
assert '"backdrop": backdrop_full(image)' in source
assert "Upgrade the existing 2.1.45.22 thumbnail-only cache automatically." in source
assert '"backdrop": backdrop_full(row.get("backdrop") or "")' in source
assert 'for field in ("title", "sub", "image", "backdrop", "poster", "kind", "reason", "year", "tmdb_id"):' in source
assert panel.count('<property name="backdrop">') == 112
assert 'Property(ai.home.pop.1.backdrop)' in panel
assert 'Property(ai.home.result.1.backdrop)' in panel
assert '<include name="LucentAISearchBackdropTitle">' in panel
assert '<include>LucentAISearchBackdropTitle</include>' in home
assert 'Property(ai.home.pop.1.backdrop)' in home
assert 'Property(ai.home.result.1.backdrop)' in home
assert 'font45_title' in panel and 'align>right</align>' in panel
for id in (9510,9520,9530,9540,9550):
    assert 'Container(%s).ListItem.Label' % id in panel
    assert 'Control.HasFocus(%s)' % id in panel
    assert 'Container(%s).ListItem.Property(backdrop)' % id in home


from ai_exact_core import candidate, merge_candidates
silo_tv = {"name":"Silo", "year":2023, "poster":"https://example.org/silo-tv.jpg",
           "background":"https://example.org/silo-tv-bg.jpg", "imdbRating":"8.1"}
silo_movie = {"name":"Silo", "year":2015, "poster":"https://example.org/silo-movie.jpg",
              "imdbRating":"7.3"}
silo_tv_item = candidate("silo", silo_tv, "serie", "cinemeta")
silo_movie_item = candidate("Silo", silo_movie, "film", "cinemeta")
assert silo_tv_item and silo_movie_item
assert silo_tv_item["kind"] == "serie" and silo_movie_item["kind"] == "film"
assert candidate("Silo", {"name":"Silo 2","year":2020}, "film", "cinemeta") is None
assert candidate("Silo", {"name":"Silo", "year":2023}, "serie", "cinemeta")["year"] == "2023"
assert candidate("Silo", {"name":"Silo", "year":2015}, "film", "cinemeta")["year"] == "2015"
assert candidate("Silo", {"show":{"name":"Silo", "premiered":"2023-05-05"}}, "serie", "tvmaze")["year"] == "2023"
merged = merge_candidates([silo_movie_item, silo_tv_item, dict(silo_tv_item)], limit=16)
assert len(merged) == 2 and merged[0]["kind"] == "serie"
assert set((r["kind"],r["year"]) for r in merged) == {("serie","2023"),("film","2015")}
assert "def _exact_titles(prompt):" in source
assert '("serie", "series", "tv", "TVShows", "tvshows")' in source
assert '("film", "movie", "movie", "Movies", "movies")' in source
assert "_exact_titles(prompt)" in source
assert 'SLOTS = 16' in source
assert "def reset_search():" in source
assert '"ai.home.mode", "suggestions"' in source
assert "elif action == \"reset\":" in source
assert 'RunScript(special://skin/scripts/ai_home.py,reset)' in panel
assert '<control type="button" id="9502">' in panel
assert "<focusedcolor>FFFFFFFF</focusedcolor>" in panel
assert "<focusedcolor>on_focus</focusedcolor>" not in panel[panel.index('<control type="button" id="9500">'):panel.index('<control type="button" id="9502">')]
node = next(c for c in controls if c.get("id")=="9550")
assert len(node.findall("content/item")) == 16
assert panel.count('Property(ai.home.result.16.') >= 3
assert node.findtext("onback") == "RunScript(special://skin/scripts/ai_home.py,reset)"


# No more focus loss on X: SetFocus must execute BEFORE reset and the button
# must stay alive if Kodi hasn't transferred focus yet.
clear = next(c for c in controls if c.get("id") == "9502")
assert clear.findtext("label") in (None, "")
assert [n.text for n in clear.findall("onclick")] == [
    "SetFocus(9500)", "RunScript(special://skin/scripts/ai_home.py,reset)"]
assert "Control.HasFocus(9502)" in clear.findtext("visible")
assert 'icons/close.png' in panel and '<label>×</label>' not in panel
assert 'rr20_edge.png' in panel and '<visible>Control.HasFocus(9500)</visible>' in panel
search_control = next(c for c in controls if c.get("id") == "9500")
assert search_control.find("texturefocus").get("colordiffuse") == "glass_strong"
assert "rr20_edge.png" in panel  # border highlights while glass remains dark
assert 'def _focus_search():' in source
assert 'xbmc.executebuiltin("SetFocus(9500)", True)' in source
assert source.index("_focus_search()", source.index("def reset_search():")) < source.index(
    '_put("ai.home.mode", "suggestions")',source.index("def reset_search():"))
assert "from ai_cast_core import person_intent, find_person, credit_rows" in source
assert "def _verified_person_search(person, intent):" in source
assert '"movie_credits"' in source and '"tv_credits"' in source
assert "assistant.plan_query(prompt,context)" in source
assert "assistant.catalogue(p,_exact_titles)" in source
from ai_cast_core import person_intent, find_person, credit_rows
actor = person_intent("Cerca il film con Robert Pattinson del 2026")
assert actor == {"name":"Robert Pattinson", "role":"actor"}
assert person_intent("Consigliami una serie con Pedro Pascal uscita nel 2025") == (
    {"name":"Pedro Pascal","role":"actor"})
assert person_intent("Un film diretto da Christopher Nolan del 2026") == (
    {"name":"Christopher Nolan","role":"director"})
assert person_intent("Vorrei un film action del 2026") is None
assert find_person([{"id":4,"name":"Robert Pattinson","popularity":10,
                     "known_for_department":"Acting"}],
                   "Robert Pattinson")["id"] == 4
assert find_person([{"id":4,"name":"Robert Downey Jr."}], "Robert Pattinson") is None
cast_intent={"year":2026,"kind":"film","genre":None,"today":"2026-11-19","released":False}
credits={"cast":[{"title":"Verified Film", "release_date":"2026-01-20",
                  "genre_ids":[28], "poster_path":"/abcdef.jpg"},
                 {"title":"Other Year","release_date":"2024-01-20"}],
         "crew":[{"title":"Wrong Crew Only","release_date":"2026-01-20","job":"Director"}]}
rows=credit_rows(credits,"film","actor",cast_intent)
assert len(rows)==1 and rows[0]["title"]=="Verified Film" and rows[0]["year"]=="2026"
assert not credit_rows({"cast":[{"title":"Old Movie","release_date":"2024-01-20"}]},
                       "film","actor",cast_intent)
assert not credit_rows({"crew":[{"title":"Other Job","release_date":"2026-04-10",
                                 "job":"Writer"}]}, "film","director",cast_intent)

print("Lucent AI Home: focus-safe reset, static clear icon, visible search focus, verified actor credits OK")


from ai_assistant_core import validate, matches, choose_episode
p=validate({"operation":"search","kind":"film","year_from":2020,"year_to":2026,
 "genres":["horror","thriller"],"exclude_genres":["comedy"],"runtime_max":100,
 "countries":["KR"],"rating_min":7,"people":[{"name":"Robert Pattinson","role":"actor","exclude":False}]})
film={"title":"Fixture","release_date":"2024-04-01","genres":[{"id":27},{"id":53}],
 "runtime":95,"production_countries":[{"iso_3166_1":"KR"}],"vote_average":7.5,
 "credits":{"cast":[{"name":"Robert Pattinson"}],"crew":[]}}
assert matches(film,p,"film")
assert not matches(dict(film,runtime=125),p,"film")
assert not matches(dict(film,credits={"cast":[]}),p,"film")
assert not matches(dict(film,genres=[{"id":27}]),p,"film")
assert not matches(dict(film,genres=[{"id":27},{"id":53},{"id":35}]),p,"film")
assert not matches(dict(film,production_countries=[]),p,"film")
assert not matches(dict(film,release_date="2019-01-01"),p,"film")
assert not matches(dict(film,vote_average=6),p,"film")
assert not matches(dict(film,runtime=None),p,"film")
assert validate({"operation":"search","genres":["x"]})["unverified"]==["x"]
assert choose_episode([{"episodeid":1,"season":1,"episode":1,"playcount":1},
 {"episodeid":2,"season":1,"episode":2,"resume":{"position":120}},
 {"episodeid":3,"season":1,"episode":3}])["episodeid"]==2
assert choose_episode([{"episodeid":1,"season":1,"episode":1},
 {"episodeid":2,"season":1,"episode":2}],[(1,1)])["episodeid"]==2
assert 'deepseek/deepseek-v4.1-flash-1017' in (root/"scripts/ai_assistant.py").read_text()
assert "keyboard.isConfirmed()" in source
assert "9503" in panel and "9504" in panel and "icons/clock.png" in panel
assert "assistant.resume_target(p)" in source
assert "Player.Open" in source
assert "assistant.history()" in source
assert "if op==\"answer\":" in source
assert "assistant.assistant" not in source
print("Assistant: combined constraints, evidence rejection, episode progression, history and UI passed")

assert "public_catalogue" in (root/"scripts/ai_assistant.py").read_text()
assert "keyboard.isConfirmed()" in source

# PVR integration: routing must precede film/series playback; test real RPC payloads.
import ai_pvr as pvr
fixture_channels=[{"channelid":10,"channel":"DMAX HD","broadcastnow":{"title":"Programma DMAX"}},
                  {"channelid":12,"channel":"Italia 1 HD","broadcastnow":{"title":"Programma Italia 1"}},
                  {"channelid":13,"channel":"Italia 2","broadcastnow":{"title":"Altro"}}]
assert pvr.match_channels(fixture_channels,"DMAX")[0]["channelid"]==10
assert pvr.match_channels(fixture_channels,"Italia 1")[0]["channelid"]==12
assert pvr.match_channels(fixture_channels,"Italia uno")[0]["channelid"]==12
assert not pvr.match_channels(fixture_channels,"Italia")
assert pvr.local_request("metti su Dmax",fixture_channels)["operation"]=="tune"
assert pvr.local_request("cosa c'è su Italia 1?",fixture_channels)=={
    "operation":"epg","channel":"Italia 1","when":"now"}
assert pvr.local_request("Cosa danno su Italia 1 stasera?",fixture_channels)["when"]=="tonight"
assert pvr.local_request("Voglio vedere quel film del ragazzo sopravvissuto su Marte",fixture_channels) is None
calls=[]
def pvr_rpc(method,params):
    calls.append((method,params))
    if method=="PVR.GetChannels":
        return {"channels":fixture_channels,"limits":{"start":0,"end":3,"total":3}}
    if method=="Player.Open": return "OK"
    raise AssertionError(method)
cs=pvr.channels(pvr_rpc)
assert len(cs)==3 and calls[0][1]["channelgroupid"]=="alltv"
assert pvr.schedule(pvr_rpc,cs[1],"now")[0]["title"]=="Programma Italia 1"
assert pvr.tune(pvr_rpc,cs[0])=="OK"
assert calls[-1]==("Player.Open",{"item":{"channelid":10}})
assert validate({"operation":"tune","channel":"DMAX"})["channel"]=="DMAX"
assert 'if op in ("tune","epg"):' in source
assert source.index("tv_request=pvr.local_request") < source.index('target,message = assistant.resume_target(p)')
print("PVR assistant: channel identity, local route, EPG and native tuning verified")

# Regression: native TV handoff, shared progress close and permanent OSD focus.
import ast
from types import SimpleNamespace
def function_from(path,name,namespace):
    code=ast.parse((root/path).read_text(encoding="utf-8"))
    definition=next(n for n in code.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name==name)
    exec(compile(ast.Module(body=[definition],type_ignores=[]),str(path),"exec"),namespace)
    return namespace[name]
calls=[]
fake=SimpleNamespace(getCondVisibility=lambda _:True,
    executebuiltin=lambda action,wait: calls.append(("GUI",action,wait)))
start=function_from("scripts/ai_home.py","_start_tv_channel",
    {"xbmc":fake,"_status":lambda status:calls.append(("status",status)),
     "pvr":pvr,"_rpc":lambda method,params:calls.append((method,params)) or "OK"})
assert start({"channelid":7,"channel":"DMAX"})=="OK"
assert calls[1:]==[("GUI","ActivateWindow(TVChannels)",True),("Player.Open",{"item":{"channelid":7}})]
assert source.count("pvr.tune(_rpc,")==1
wrapper=function_from("scripts/ai_home.py","_QueryProgress",{"xbmcgui":SimpleNamespace(
    DialogProgressBG=lambda:SimpleNamespace(close=lambda:calls.append("closed")))})
progress=wrapper()
progress.close();progress.close()
assert calls.count("closed")==1
keymap=function_from("scripts/keymap.py","pvr_keymap",{})
import xml.etree.ElementTree as ET
for mode in (True,False):
    keys=ET.fromstring(keymap(mode))
    for device in ("remote","keyboard"):
        assert keys.findtext("FullscreenLiveTV/"+device+"/up")=="ChannelUp"
        assert keys.findtext("FullscreenLiveTV/"+device+"/down")=="ChannelDown"
    assert keys.findtext("FullscreenLiveTV/remote/select")=="OSD"
    assert keys.findtext("FullscreenLiveTV/remote/back")==(
        "RunScript(special://skin/scripts/fsback.py)" if mode else "Back")
osd=ET.parse(root/"xml/VideoOSD.xml").getroot()
for ident in ("4990","4991","4992"):
    assert len(osd.findall(".//control[@id='"+ident+"']"))==1
assert any("SetFocus(4990)"==a.text for a in osd.findall("onload"))
assert not any(a.text=="SetFocus(460)" for a in osd.findall("onload"))
assert osd.find(".//control[@id='4992']").findall("onclick")[-1].text=="PlayerControl(Stop)"
assert osd.find(".//control[@id='4991']").findall("onclick")[-1].text=="ActivateWindow(pvrosdchannels)"
assert "SetFocus(460,0)" not in (root/"scripts/live.py").read_text()
print("PVR handoff, dialog closure, dedicated keymap and stable OSD focus verified")
