"""The type checker's verdict, held to the map (goals/p1-types-hold.yaml).

pyright reads every engine file at its basic level and the base and the maths library strictly (`[tool.pyright]`
in pyproject.toml, the version pinned there). Nothing it calls wrong may stand anywhere. The one thing allowed to
stand is a missing annotation in `assess/` — a parameter, a variable or a value whose type nobody wrote down —
counted per file in workflows.json (`types.frozen`) at exactly today's number: a file that sheds some writes its new
number down, and none grows back (`engine ratchet` holds the map to the commit before).
"""

import json
import subprocess
import sys
import tomllib
from collections import Counter
from pathlib import Path

import pytest

from engine.core import db

ENGINE = db.REPO_ROOT / "packages" / "engine"
TYPES = json.loads((db.REPO_ROOT / "workflows.json").read_text())["types"]
PYRIGHT = tomllib.loads((ENGINE / "pyproject.toml").read_text())["tool"]["pyright"]


@pytest.fixture(scope="module")
def verdict() -> list[tuple[str, str, int, str]]:
    """(file, rule, line, message) for every error pyright finds, each file as the map names it."""
    run = subprocess.run(
        [sys.executable, "-m", "pyright", "--outputjson"],
        cwd=ENGINE,
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert run.stdout, run.stderr
    report = json.loads(run.stdout)
    assert report["summary"]["filesAnalyzed"] > 100, (
        "pyright read too few files: is [tool.pyright] still there?"
    )
    return [
        (
            Path(d["file"]).relative_to(ENGINE).as_posix(),
            d.get("rule", ""),
            d["range"]["start"]["line"] + 1,
            d["message"].split("\n")[0],
        )
        for d in report["generalDiagnostics"]
        if d["severity"] == "error"
    ]


def test_nothing_the_type_checker_calls_wrong_stands(verdict):
    """A value that may be None used as if it never is, a call its callee does not take, an operation its types do
    not have, a name nothing reads: each one is fixed where it is, in every engine file."""
    assert PYRIGHT["include"] == ["engine"] and PYRIGHT["typeCheckingMode"] == "basic"
    wrong = [f"{f}:{n} {rule}: {msg}" for f, rule, n, msg in verdict if rule not in TYPES["unannotated"]]
    assert wrong == []


def test_the_base_is_strict_and_clean(verdict):
    """`core/` — the one connection, the loader, the class list, every workflow's footing — read strictly, with
    nothing standing: not even a missing annotation."""
    assert "engine/core" in PYRIGHT["strict"]
    assert [f"{f}:{n} {rule}: {msg}" for f, rule, n, msg in verdict if f.startswith("engine/core/")] == []


def test_missing_annotations_stand_only_where_frozen_and_only_fall(verdict):
    """The maths library is read strictly too; what it has not yet written down is today's debt, counted per file.
    A count that rose, a file new to the list, or a count that fell and was not written down each fail here."""
    assert "engine/assess" in PYRIGHT["strict"]
    counted = dict(sorted(Counter(f for f, rule, *_ in verdict if rule in TYPES["unannotated"]).items()))
    frozen = TYPES["frozen"]
    changed = {f: (frozen.get(f, 0), counted.get(f, 0)) for f in counted.keys() | frozen.keys()}
    assert {f: was_now for f, was_now in changed.items() if was_now[0] != was_now[1]} == {}, (
        "(frozen, today) per file: fix what rose, and write down what fell in workflows.json `types.frozen`"
    )
