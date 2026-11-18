#!/usr/bin/env python3
"""Smoke tests that exercise Lucent's Italian localisation without Kodi installed.

Extract only the pure translation functions from the Kodi scripts: no Android,
TMDb, network, or Kodi dependencies are executed.
"""
import ast
import pathlib
import runpy
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
lang = runpy.run_path(str(ROOT / "scripts/lang_it.py"))
assert lang["translate"]("Next") == "Avanti"
assert lang["translate"]("Step 5 of 9") == "Passaggio 5 di 9"
assert len(lang["STEPS"]) == 10
for key, (title, body) in lang["STEPS"].items():
    assert title and body, key

def compiled_function(file, name, state, literal_dict=None):
    original = ast.parse((ROOT / "scripts" / file).read_text(encoding="utf-8"))
    fn = next(x for x in original.body if isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef)) and x.name == name)
    scope = dict(state)
    if literal_dict:
        obj = next(x for x in original.body if isinstance(x, ast.Assign)
                   and any(isinstance(t, ast.Name) and t.id == literal_dict for t in x.targets))
        scope[literal_dict] = ast.literal_eval(obj.value)
    compiled = compile(ast.fix_missing_locations(ast.Module(body=[fn], type_ignores=[])), file, "exec")
    exec(compiled, scope)
    return scope[name]

step_t = compiled_function("setup.py", "t", {"IT": True, "NL": False})
step_label = compiled_function("setup.py", "localized_step", {"IT": True, "NL": False})
assert step_t("Next", "Volgende") == "Avanti"
assert step_t("No TMDb key yet", "Nog geen TMDb-sleutel") == "Nessuna chiave TMDb"
assert step_label("play", ("Picture and sound", "Beeld en geluid"), 0) == "Immagine e audio"
assert "frequenza" in step_label("play", ("English placeholder", "Dutch placeholder"), 1)
assert compiled_function("setup.py", "t", {"IT": False, "NL": True})("Next", "Volgende") == "Volgende"
assert compiled_function("setup.py", "t", {"IT": False, "NL": False})("Next", "Volgende") == "Next"

menu_it = compiled_function("menu.py", "tr", {"_IT": True, "_NL": False}, "T")
assert menu_it("t_movies") == "Film"
assert menu_it("w_recent_m") == "Film aggiunti di recente"
assert "Film" in menu_it("remove_tab_q", "Film")
menu_nl = compiled_function("menu.py", "tr", {"_IT": False, "_NL": True}, "T")
assert menu_nl("t_movies") == "Films"
menu_en = compiled_function("menu.py", "tr", {"_IT": False, "_NL": False}, "T")
assert menu_en("t_movies") == "Movies"

info_it = compiled_function("info.py", "tr", {"_IT": True, "_NL": False}, "T")
assert info_it("library") == "Raccolta Trakt"
assert info_it("saved") == "Salvato"
assert "Film" in info_it("added_to", "Film", "Trakt")

print("PASS: Italian, English and Dutch setup, menu and movie-info translation smoke tests")
