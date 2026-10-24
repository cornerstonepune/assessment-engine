"""UX9b (goals/ux9b-regroup.yaml): the school's word is "regroup".

Nimish, 2026-10-22, on the audit's question D1 (addition's skills said "carrying", subtraction's "exchanging", and the
school's rule names "exchange / regroup"): he chose "regroup". So no person reads "carry", "carrying" or "borrow" for a
column that passes ten, anywhere: a screen, a printed paper, a mistake's name, a level's words, a parent's report.

Every string a person can be shown is read here: the website's code with its comments taken out, every string in the
engine's code that is not a docstring (a code, a key or a pattern, with no space in it, is not words), the engine's
story templates, and every string the seed loads. Left out, each for its reason: a gold file is what a person or a model
once wrote, kept as it was to score against; a past paper (`seed/papers`) is what the school printed, kept as printed; a prompt is words to a model, whose words to a parent are held by
`parent_check` (a parent report with "carry" in it is refused there).
"""

import ast
import json
import os
import re
from pathlib import Path

import pytest

from engine.core import db, school_words
from engine.w4_close import parent_check

ROOT = db.REPO_ROOT
# the rule is the engine's (engine/core/school_words.py), so what an educator saves is held by it too
SAID, NOT_SUMS = school_words.SAID, school_words.NOT_SUMS
WEB = ("apps/web/app", "apps/web/lib", "apps/web/components")
_COMMENTS = re.compile(r"/\*.*?\*/|(?<![:\"'`\w])//[^\n]*", re.DOTALL)


def _said(where: str, text: str) -> list[str]:
    # a CSS class is not words: the printed paper's room for a regrouped digit is `.g.carry`
    text = re.sub(r'class(?:Name)?="[^"]*"|\.[\w.-]*carry\b', "", NOT_SUMS.sub("", text))
    return [f"{where}: …{text[max(0, m.start() - 40) : m.end() + 40]}…" for m in SAID.finditer(text)]


def _strings(x):
    if isinstance(x, str):
        yield x
    elif isinstance(x, dict):
        for v in x.values():
            yield from _strings(v)
    elif isinstance(x, list):
        for v in x:
            yield from _strings(v)


def _python_words(path: Path):
    tree = ast.parse(path.read_text())
    docs = {
        id(n.body[0].value)
        for n in ast.walk(tree)
        if isinstance(n, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef)
        and n.body
        and isinstance(n.body[0], ast.Expr)
        and isinstance(n.body[0].value, ast.Constant)
    }
    for n in ast.walk(tree):
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docs and " " in n.value:
            yield n.lineno, n.value


def test_no_screen_says_carry_or_borrow():
    found = []
    for top in WEB:
        for p in sorted((ROOT / top).rglob("*.ts*")):
            found += _said(str(p.relative_to(ROOT)), _COMMENTS.sub("", p.read_text()))
    assert found == []


def test_no_printed_paper_mistake_or_report_the_engine_writes_says_carry_or_borrow():
    found = []
    for p in sorted((ROOT / "packages/engine/engine").rglob("*.py")):
        if p == ROOT / "packages/engine/engine/core/school_words.py":
            continue  # the rule's own patterns name the words
        for line, s in _python_words(p):
            found += _said(f"{p.relative_to(ROOT)}:{line}", s)
    for p in sorted((ROOT / "packages/engine/engine").rglob("*.json")):
        found += [w for s in _strings(json.loads(p.read_text())) for w in _said(str(p.relative_to(ROOT)), s)]
    assert found == []


def test_no_row_the_seed_loads_says_carry_or_borrow():
    found = []
    for p in sorted((ROOT / "supabase/seed").rglob("*.json")):
        if p.name.endswith("_gold.json") or p.name == "prompts.json" or p.parent.name == "papers":
            continue
        found += [
            w
            for s in _strings(json.loads(p.read_text()))
            if " " in s
            for w in _said(str(p.relative_to(ROOT)), s)
        ]
    assert found == []


def test_a_parent_report_that_says_carry_is_refused_and_one_that_says_regroup_is_not():
    banned = [re.compile(rf"\b{w}\b", re.IGNORECASE) for w in parent_check.BANNED]
    said = lambda t: any(b.search(t) for b in banned)  # noqa: E731
    assert said("She sometimes forgets to carry the ten.")
    assert said("Carrying in the tens column is getting steadier.")
    assert not said("She sometimes forgets to regroup the ten.")
    assert not said("Together you can carry out one sum at home.")


ROWS = {
    "skill": ("name", "learning_objective", "difficulty", "descriptor"),
    "skill_level": ("looks_like",),
    "misconception": ("name", "description", "repair_hint"),
    "taxonomy_case": ("section_name", "label", "example_text"),
    "case_dimension": ("description",),
    "report_item": ("title",),
}


@pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs the local copy (bin/testdb)")
def test_no_row_a_person_reads_says_carry_or_borrow_once_the_migration_and_the_seed_have_run():
    """A skill's words are not the seed's to overwrite (they are approved on the site): the migration replaces the
    seed's old words where they still stand, and the loader the rest."""
    found = []
    with db.connect(db.dsn()) as conn:
        for table, cols in ROWS.items():
            for col in cols:
                for r in conn.execute(
                    f"select {col}::text as t from {table} where {col}::text ~* 'carr|borrow'"
                ):  # noqa: S608
                    found += _said(f"{table}.{col}", r["t"])
    assert found == []
