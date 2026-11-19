"""Offline contract/regression tests for Lucent AI Search (no Kodi installation required)."""
import os
import sys
import json
import xml.etree.ElementTree as ET
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from ai_search_core import stream4me_url, parse_ai, matches_live, is_default_search
r = Path(__file__).resolve().parent.parent
u = stream4me_url("Silo & MobLand, 2025")
assert u == "plugin://plugin.video.s4me/?channel=search&action=new_search&mode=all&search_text=Silo%20%26%20MobLand%2C%202025"
assert "search_text=" in u and "channel=search&action=new_search&mode=all" in u
for q in ("", "   ", "x"*300):
    try: stream4me_url(q); raise AssertionError("invalid title accepted")
    except ValueError: pass
rows, message = parse_ai('z ```json\n{"message":"Ecco","titles":[{"title":"John Wick","year":2014,"type":"movie","reason":"Azione"},{"title":"Silo","type":"tvshow"},{"title":"Silo"}]}\n``` z')
assert len(rows) == 2 and rows[1]["kind"] == "serie" and rows[0]["year"] == "2014"
assert message == "Ecco"
assert rows[0]["title"] == "John Wick" and rows[1]["title"] == "Silo"
# Free-router regressions: JSON arrays, localized keys and plain numbered titles.
rows, _ = parse_ai('[{"title":"Severance","type":"tvshow"},{"titolo":"Dark","type":"serie"}]')
assert [x["title"] for x in rows] == ["Severance", "Dark"]
assert all(x["kind"] == "serie" for x in rows)
rows, _ = parse_ai('{"messaggio":"Prova queste","consigli":[], "titoli":[{"titolo":"Fallout","type":"tv"}]}')
assert len(rows) == 1 and rows[0]["title"] == "Fallout"
rows, _ = parse_ai("Ecco delle serie simili:\n1. **Severance** - mistero\n2. Dark (2017)\n3. Fallout: fantascienza")
assert [x["title"] for x in rows] == ["Severance", "Dark", "Fallout"]
rows, _ = parse_ai('Risultati:\n- Andor\n- Black Mirror')
assert [x["title"] for x in rows] == ["Andor", "Black Mirror"]
for invalid in ("", "   ", None):
    try: parse_ai(invalid); raise AssertionError("invalid AI response accepted")
    except ValueError: pass
assert parse_ai("Nessuna idea disponibile.") == ([], "")
assert matches_live("Il padrino", "Il Padrino (film)") and not matches_live("azione", "Film d'azione")
assert is_default_search("icons/search.png","VideoLibrary.Search")
assert not is_default_search("icons/search.png","ActivateWindow(Settings)")
ui = ET.parse(r / "xml/Lucent_AISearch.xml").getroot()
ids = {int(c.get("id")):c for c in ui.iter("control") if c.get("id")}
assert {10,11,12,13,14,50,90}.issubset(ids)
assert int(ids[10].findtext("height")) >= 72
menu = (r / "scripts/menu.py").read_text(encoding="utf-8")
assert menu.count("RunScript(special://skin/scripts/ai_search.py)") >= 2
startup = (r / "scripts/startup.py").read_text(encoding="utf-8")
assert 'ai_search.install_menu' in startup
home_source = (r / "xml/Home.xml").read_text(encoding="utf-8")
assert "ai_search.py,setupmenu" in home_source

# Artwork and visual contracts: no extra key required, exact-title matching.
from ai_art_core import choose_record, tmdb_art, catalogue_art, metadata_label, safe_image
assert choose_record([{"name":"Silo", "first_air_date":"2023-05-05"}], "Silo")["name"] == "Silo"
assert choose_record([{"name":"Snowpiercer", "first_air_date":"2020-01-01"},
                      {"name":"Snowpiercer", "first_air_date":"2013-01-01"}],
                     "Snowpiercer", "2020")["first_air_date"].startswith("2020")
assert choose_record([{"name":"Silo 2"}], "Silo") is None
assert choose_record([{"original_name":"La casa di carta", "name":"Money Heist"}],
                     "La casa di carta")
assert tmdb_art({"poster_path":"/abc123.jpg", "backdrop_path":"/xyz789.jpg",
                 "first_air_date":"2023-01-01", "vote_average":8.24}) == {
    "poster":"https://image.tmdb.org/t/p/w342/abc123.jpg",
    "backdrop":"https://image.tmdb.org/t/p/w780/xyz789.jpg",
    "year":"2023", "rating":"8.2"}
assert catalogue_art({"poster":"https://images.metahub.space/poster/test",
                      "name":"Silo", "year":"2023", "imdbRating":"8.1"},
                     "cinemeta")["poster"].startswith("https://")
assert catalogue_art({"name":"Silo", "image":{"medium":"https://static.tvmaze.com/i.jpg"},
                      "premiered":"2023-01-01"}, "tvmaze")["year"] == "2023"
assert not safe_image("javascript:alert(1)") and not safe_image("http://not-secure.test/img")
assert metadata_label({"kind":"serie","year":"2023","rating":"8.2"}) == "SERIE TV  ·  2023  ·  ★ 8.2"
ai_ui = r / "xml/Lucent_AISearch.xml"
xml_source = ai_ui.read_text(encoding="utf-8")
assert '<orientation>horizontal</orientation>' in xml_source
assert "ListItem.Art(poster)" in xml_source and "Container(50).ListItem.Property(reason)" in xml_source
assert "rr20_edge.png" in xml_source and "mask_poster.png" in xml_source
assert not any(int(c.findtext("width","0")) > 1920 for c in ui.iter("control") if c.find("width") is not None and c.findtext("width","0").isdigit())
script = (r/"scripts/ai_search.py").read_text(encoding="utf-8")
assert "_add_artwork(" in script and 'item.setArt(artwork)' in script
assert "stream4me_url(title)" in script and "self.setFocusId(50)" in script


# Correct year semantics, direct-title handling and independent checks.
import datetime
from ai_intent_core import understand, year_eligible, genre_eligible
today = datetime.date(2026, 11, 19)
f = understand("Voglio vedere un film action uscito quest'anno", today)
assert f["year"] == 2026 and f["genre"] == "action" and f["kind"] == "film"
assert f["released"] and not f["direct"]
assert understand("Consigliami una serie come Silo", today)["direct"] is False
assert understand("un film simile a Silo", today)["direct"] is False
assert understand("mammina", today)["direct"] is True
assert understand("from", today)["direct"] is True
assert understand("pirati dei caraibi", today)["direct"] is True
assert understand("film action 2025", today)["year"] == 2025
assert understand("film dell'anno scorso", today)["year"] == 2025
assert not year_eligible({"year": "2026"}, f)  # LLM's own year cannot verify a film
assert not year_eligible({"verified_year": "2025"}, f)
assert not year_eligible({"verified_year": "2024"}, f)
assert year_eligible({"verified_year": "2026"}, f)
assert not genre_eligible({"genre_ids": [35, 18]}, f)
assert genre_eligible({"genre_ids": [28, 53]}, f)
assert genre_eligible({"genres": ["Action", "Thriller"]}, f)
script = (r / "scripts/ai_search.py").read_text(encoding="utf-8")
assert "_ai_request(self.prompt, key, intent)" in script
assert "self.prompt.strip()" in script and "Ricerca per titolo esatto" in script
assert "primary_release_date.gte" in script and "primary_release_date.lte" in script
assert "v3-cinemeta.strem.io/catalog/movie/top" in script
assert "row[\"verified_year\"]" in script and "year_eligible(row, intent)" in script
assert "rows = _add_artwork(verified + suggestions, intent)" in script
assert "Nessun titolo del %d verificabile" in script
ui_string = (r/"xml/Lucent_AISearch.xml").read_text(encoding="utf-8")
assert "Container(50).ListItem.Label" in ui_string

print("Lucent AI: dates verified, direct titles, catalogue discovery, Stream4Me route and artwork")
