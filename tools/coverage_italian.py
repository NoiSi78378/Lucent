#!/usr/bin/env python3
"""Audit translated Python labels; report untranslated bilingual strings."""
import ast
import pathlib
import runpy
import re

root = pathlib.Path(__file__).resolve().parents[1]
data = runpy.run_path(str(root / "scripts/lang_it.py"))
translated = data["TEXT"]
translate = data["translate"]
format_errors = []
untranslated = {}
incompatible = {}
for path in sorted((root / "scripts").glob("*.py")):
    if path.name in ("lang_it.py", "setup.py"):
        continue
    raw = path.read_text(encoding="utf-8")
    if "lang_it" not in raw:
        continue
    module = ast.parse(raw)
    items = set()
    for node in ast.walk(module):
        if isinstance(node, ast.Tuple) and len(node.elts) == 2:
            pair = node.elts
            if all(isinstance(x, ast.Constant) and isinstance(x.value, str) for x in pair):
                a,b = [x.value for x in pair]
                if path.name == "libtools.py":
                    a,b = b,a
                if len(a) >= 4 and a != b and not a.startswith(("plugin://","special://","https://")):
                    items.add(a)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ("t", "tr", "G") and len(node.args) >= 2:
            args = node.args[:2]
            if all(isinstance(x, ast.Constant) and isinstance(x.value, str) for x in args):
                a,b = [x.value for x in args]
                if path.name == "libtools.py":
                    a,b = b,a
                if len(a)>=4 and a!=b:
                    items.add(a)
    missing = sorted(s for s in items if translate(s) == s and not s.startswith(("/",".","[","$")) and not re.fullmatch(r"[a-zA-Z0-9_./:=-]+",s) and not any(t in s for t in ("kind=", "mediatype=", "traktlists&", "mdblists&")))
    if missing:
        untranslated[path.name] = missing
    # String formatting placeholders must survive translation unchanged.
    for english in items:
        italian = translate(english)
        if english == italian:
            continue
        fields = lambda text: sorted(re.findall(r'(?<!\{)\{(?:[a-zA-Z_][\w]*|\d*)\}(?!\})', text))
        if fields(english) != fields(italian):
            format_errors.append((path.name, english[:120], fields(english), fields(italian)))
    incompatible[path.name] = len(items)
print(f"TOTAL literal pairs: {sum(incompatible.values())}")
print(f"TOTAL likely missing Italian labels: {sum(len(a) for a in untranslated.values())}")
for file, phrases in untranslated.items():
    print(f"MISSING {file}: {len(phrases)}")
    for label in phrases[:250]:
        print("  *",repr(label))

if untranslated:
    raise SystemExit("Found untranslated user-facing strings; correct them before release")

print("Placeholder mismatches:", len(format_errors))
for item in format_errors[:50]:
    print("FORMAT", item)
if format_errors:
    raise SystemExit("Dynamic placeholders differ from the original strings")
