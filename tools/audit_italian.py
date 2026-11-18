#!/usr/bin/env python3
"""Static audit of the Italian skin fork. Run from repository root."""
import ast
import pathlib
import re
import sys
import xml.etree.ElementTree as ET

root = pathlib.Path(__file__).resolve().parents[1]
en = (root / "language/resource.language.en_gb/strings.po").read_text(encoding="utf-8")
it = (root / "language/resource.language.it_it/strings.po").read_text(encoding="utf-8")
rx = r'^msgctxt "#(\d+)"\s*\nmsgid "((?:\\.|[^"])*)"\s*\nmsgstr "((?:\\.|[^"])*)"'
entries = lambda s: {m.group(1): (m.group(2), m.group(3)) for m in re.finditer(rx, s, re.M)}
en_entries, it_entries = entries(en), entries(it)
missing = sorted(set(en_entries) - set(it_entries))
empty = [k for k, v in it_entries.items() if not v[1]]
print(f"Catalogue: EN {len(en_entries)}, IT {len(it_entries)}, missing={len(missing)}, empty={len(empty)}")
if missing or empty:
    print("Missing/empty ids:", missing[:100], empty[:100])
    sys.exit(1)

errors, literal_labels = [], []
for p in root.rglob("*.xml"):
    if ".github" in p.parts:
        continue
    try:
        tree = ET.parse(p)
    except Exception as exc:
        errors.append((str(p.relative_to(root)), str(exc)))
        continue
    for node in tree.iter():
        if node.tag.lower() in ("label", "description", "text", "heading") and node.text:
            content = node.text.strip()
            if content and re.search(r"[A-Za-z]{3}", content) and not content.startswith(("$", "[")):
                literal_labels.append((str(p.relative_to(root)), node.tag, content[:100]))
print(f"XML parse errors: {len(errors)} / literal labels: {len(literal_labels)}")
for item in errors[:50]:
    print("XML error", item)
for item in literal_labels[:60]:
    print("XML untranslated candidate", item)

report = []
for p in sorted((root / "scripts").glob("*.py")):
    raw = p.read_text(encoding="utf-8")
    try:
        tree = ast.parse(raw)
    except SyntaxError as exc:
        print(f"PY syntax error {p.name}: {exc}")
        sys.exit(2)
    pairs = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ("t", "tr", "G") and len(node.args) >= 2:
            a, b = node.args[:2]
            if isinstance(a, ast.Constant) and isinstance(a.value, str) and isinstance(b, ast.Constant) and isinstance(b.value, str):
                pairs.append((a.value, b.value, node.lineno))
        if isinstance(node, ast.Tuple) and len(node.elts) == 2 and all(isinstance(x, ast.Constant) and isinstance(x.value, str) for x in node.elts):
            en_label, nl_label = [x.value for x in node.elts]
            if en_label != nl_label and len(en_label) >= 4 and re.search(r"[a-zA-Z]", en_label):
                pairs.append((en_label, nl_label, node.lineno))
    if pairs and "lang_it" not in raw:
        report.append((p.name, len(pairs), pairs[:5]))
print(f"Scripts with bilingual text but no Italian translation integration: {len(report)}")
for name, count, samples in report:
    print("PY unlocalized", name, count, samples)
if errors:
    sys.exit(3)
