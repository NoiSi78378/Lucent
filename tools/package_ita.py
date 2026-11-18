#!/usr/bin/env python3
"""Make an independent Lucent (Italiano) installable package.

Only operates on the staging folder, never on the upstream fork files.
Kodi skins should have distinct IDs when installed side-by-side.
"""
import pathlib
import re
import sys
import xml.etree.ElementTree as ET

if len(sys.argv) != 2:
    raise SystemExit("Usage: package_ita.py /staging/skin.lucent.ita")

root = pathlib.Path(sys.argv[1]).resolve()
assert root.name == "skin.lucent.ita", root
assert (root / "addon.xml").is_file()
assert (root / "scripts/updater.py").is_file()
if not (root / "scripts/updater.py").read_text(encoding="utf-8").count('if addon_id.startswith("skin.")'):
    raise SystemExit("Updater guard missing: may overwrite Italian skin")

old_id = re.compile(r'(?<![A-Za-z0-9_.])skin\.lucent(?!\.ita)')
rewritten = 0
for p in root.rglob("*"):
    if not p.is_file() or p.suffix not in (".xml", ".py", ".po", ".json", ".txt", ".ini", ".cfg", ".xsp", ".md"):
        continue
    content = p.read_text(encoding="utf-8")
    replaced, n = old_id.subn("skin.lucent.ita", content)
    if n:
        p.write_text(replaced, encoding="utf-8")
        rewritten += n
    if old_id.search(replaced):
        raise SystemExit(f"Original skin ID remains in {p}")

addon = ET.parse(root / "addon.xml").getroot()
assert addon.attrib["id"] == "skin.lucent.ita"
assert addon.attrib["name"] == "Lucent (Italiano)"
assert (root / "language/resource.language.it_it/strings.po").is_file()
assert (root / "scripts/lang_it.py").is_file()

print(f"Built independent {addon.attrib['name']} {addon.attrib['version']}")
print(f"Rewrote {rewritten} references to the original skin ID")
