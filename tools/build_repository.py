#!/usr/bin/env python3
"""Build a self-contained Kodi repository and HTTP browse index for Lucent ITA.

Requires a staged skin folder named skin.lucent.ita. Publishes a repository
installer as a small ZIP in the web root, and the actual skin ZIP under the
canonical Kodi add-on datadir. GitHub Pages can serve these as static files.
"""
from pathlib import Path
import hashlib
import os
import sys
import xml.etree.ElementTree as ET
from zipfile import ZipFile, ZIP_DEFLATED

if len(sys.argv) != 3:
    raise SystemExit("Usage: build_repository.py /path/to/skin.lucent.ita /path/to/site")
skin = Path(sys.argv[1]).resolve()
site = Path(sys.argv[2]).resolve()
assert skin.name == "skin.lucent.ita", "Skin must be staged under skin.lucent.ita"
skin_xml = (skin / "addon.xml").read_text(encoding="utf-8")
skin_addon = ET.fromstring(skin_xml)
assert skin_addon.attrib["id"] == "skin.lucent.ita"
version = skin_addon.attrib["version"]
assert version == "2.1.45.1", version

repo_id = "repository.lucent.ita"
repo_version = "1.0.1"
base = "https://noisi78378.github.io/Lucent"
repo_url = f"{base}/repo-ita"
skin_zip = site / "repo-ita" / "zips" / skin_addon.attrib["id"] / f"{skin.name}-{version}.zip"
skin_zip.parent.mkdir(parents=True, exist_ok=True)

def zip_folder(archive_path, root):
    with ZipFile(archive_path, "w", ZIP_DEFLATED, compresslevel=6) as z:
        for p in sorted(root.rglob("*")):
            if p.is_file() and p.suffix != ".pyc" and "__pycache__" not in p.parts:
                z.write(p, arcname=f"{root.name}/{p.relative_to(root).as_posix()}")
    with ZipFile(archive_path) as z:
        assert z.testzip() is None, archive_path

zip_folder(skin_zip, skin)
repo_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<addon id="{repo_id}" name="Lucent ITA Repository" version="{repo_version}" provider-name="Lucent ITA community translation">
  <extension point="xbmc.addon.repository">
    <dir>
      <info compressed="false">{repo_url}/addons.xml</info>
      <checksum>{repo_url}/addons.xml.md5</checksum>
      <datadir zip="true">{repo_url}/zips/</datadir>
      <hashes>false</hashes>
    </dir>
  </extension>
  <extension point="xbmc.addon.metadata">
    <summary lang="it_IT">Repository della traduzione italiana di Lucent</summary>
    <summary lang="en_GB">Repository for the Lucent Italian skin translation</summary>
    <description lang="it_IT">Distribuisce Lucent (Italiano) separatamente dalla skin originale, mantenendo le attribuzioni a Wilfried van der Voort.</description>
    <description lang="en_GB">Independent Italian localization of the Lucent Kodi skin by Wilfried van der Voort.</description>
    <platform>all</platform>
    <license>GPL-2.0-or-later</license>
  </extension>
</addon>
"""
repo_dir = site / repo_id
repo_dir.mkdir(parents=True, exist_ok=True)
(repo_dir / "addon.xml").write_text(repo_xml, encoding="utf-8")
repo_zip = site / f"{repo_id}-{repo_version}.zip"
repo_zip_alias = site / f"{repo_id}.zip"
zip_folder(repo_zip, repo_dir)
repo_zip_alias.write_bytes(repo_zip.read_bytes())

# Kodi repository folders always store ZIPs under the declared add-on ID.
repo_dist_dir = site / "repo-ita" / "zips" / repo_id
repo_dist_dir.mkdir(parents=True, exist_ok=True)
(repo_dist_dir / repo_zip.name).write_bytes(repo_zip.read_bytes())

addons_text = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<addons>\n' + skin_xml.split("?>", 1)[-1].strip() + "\n" + repo_xml.split("?>", 1)[-1].strip() + "\n</addons>\n"
addons_path = site / "repo-ita" / "addons.xml"
addons_path.write_text(addons_text, encoding="utf-8")
(site / "repo-ita" / "addons.xml.md5").write_text(hashlib.md5(addons_text.encode("utf-8")).hexdigest(), encoding="utf-8")

index = """<!DOCTYPE html>
<html lang="it"><head><meta charset="utf-8">
<title>Lucent ITA – Repository Kodi</title></head>
<body><h1>Lucent ITA – Repository Kodi</h1>
<p>In Kodi: Impostazioni → Gestione file → Aggiungi sorgente → inserisci l'indirizzo di questa pagina.</p>
<p>Poi vai in Add-on → Installa da file ZIP → Lucent ITA → scegli il repository qui sotto.</p>
<p><a href="repository.lucent.ita-1.0.1.zip">repository.lucent.ita-1.0.1.zip (versione corretta per Kodi 20+)</a></p>
<p><a href="repository.lucent.ita.zip">repository.lucent.ita.zip</a></p>
<p>Una volta installato, seleziona Installa da repository → Lucent ITA Repository → Aspetto e interfaccia → Skin → Lucent (Italiano).</p>
<p>Skin originale: <a href="https://github.com/djdirty60/Lucent">djdirty60/Lucent</a>. Licenza GPL-2.0-or-later.</p>
</body></html>
"""
(site / "index.html").write_text(index, encoding="utf-8")
(site / ".nojekyll").write_text("", encoding="utf-8")

# Verify canonical paths and repository manifest agree.
listed = ET.parse(addons_path).getroot()
assert set(x.attrib["id"] for x in listed.findall("addon")) == {skin.name, repo_id}
repo_extension = ET.fromstring(repo_xml).find("./extension[@point='xbmc.addon.repository']")
assert repo_extension is not None
repo_dirs = repo_extension.findall("dir")
assert len(repo_dirs) == 1, "Kodi 20+ requires a <dir> repository definition"
assert repo_dirs[0].findtext("info") == f"{repo_url}/addons.xml"
assert repo_dirs[0].findtext("checksum") == f"{repo_url}/addons.xml.md5"
assert repo_dirs[0].findtext("datadir") == f"{repo_url}/zips/"
with ZipFile(skin_zip) as z:
    assert f"{skin.name}/addon.xml" in z.namelist()
with ZipFile(repo_zip) as z:
    assert f"{repo_id}/addon.xml" in z.namelist()
print(f"Repository validated: {repo_id} {repo_version}, {skin.name} {version}")
print(f"Website URL: {base}/")
print(f"Skin ZIP: {skin_zip.stat().st_size} bytes / Repo installer: {repo_zip.stat().st_size} bytes")
