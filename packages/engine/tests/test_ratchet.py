"""The baselines only tighten (goals/p1-the-gates-hold.yaml).

Each frozen number in `workflows.json` and the coverage floor in `pyproject.toml` is held to the commit before
by `engine ratchet --base <commit>`, which CI runs on every change. These pin what counts as loosening.
"""

import json

from engine.checks import ratchet

BASE = {
    "ceiling": 400,
    "covers": ["engine/", "apps/web/"],
    "ceilings": {"engine/big.py": 500, "apps/web/tests/e2e.spec.ts": 466},
    "complexity": {"limit": {"C901": 10, "PLR0915": 50}, "frozen": {"engine/a.py::f": {"C901": 20}}},
    "coverage": 79.0,
}


def _with(**changes):
    return {**json.loads(json.dumps(BASE)), **changes}


def test_tightening_or_standing_still_passes():
    assert ratchet.loosened(BASE, BASE) == []
    tighter = _with(
        ceilings={"engine/big.py": 450},
        complexity={"limit": {"C901": 10, "PLR0915": 50}, "frozen": {}},
        coverage=80.5,
    )
    assert ratchet.loosened(BASE, tighter) == []


def test_a_baseline_may_only_tighten():
    """Raising a limit, growing a frozen number, freezing something new, dropping what is measured, or lowering
    the coverage floor: each is a red build, never a quiet edit (CLAUDE.md rule 14)."""
    cases = {
        "ceiling": _with(ceiling=450),
        "grown file": _with(ceilings={**BASE["ceilings"], "engine/big.py": 520}),
        "newly frozen file": _with(ceilings={**BASE["ceilings"], "engine/new.py": 410}),
        "unmeasured website": _with(covers=["engine/"]),
        "raised limit": _with(complexity={"limit": {"C901": 12, "PLR0915": 50}, "frozen": {"engine/a.py::f": {"C901": 20}}}),
        "grown function": _with(complexity={"limit": {"C901": 10, "PLR0915": 50}, "frozen": {"engine/a.py::f": {"C901": 21}}}),
        "newly frozen function": _with(
            complexity={"limit": {"C901": 10, "PLR0915": 50}, "frozen": {"engine/a.py::f": {"C901": 20}, "engine/b.py::g": {"C901": 11}}}
        ),
        "new rule on a frozen function": _with(
            complexity={"limit": {"C901": 10, "PLR0915": 50}, "frozen": {"engine/a.py::f": {"C901": 20, "PLR0915": 60}}}
        ),
        "complexity gone": _with(complexity=None),
        "lower floor": _with(coverage=78.5),
    }  # fmt: skip
    for case, head in cases.items():
        assert ratchet.loosened(BASE, head), f"{case} passed as if it tightened"


def test_a_baseline_written_down_for_the_first_time_is_not_a_loosening():
    """Main before this goal measured the engine alone and had no complexity list: the website's e2e.spec.ts
    frozen at 466 and the 30 functions recorded are today's debt written down, not new debt."""
    before = _with(covers=["engine/"], ceilings={"engine/big.py": 500}, complexity=None, coverage=0.0)
    assert ratchet.loosened(before, BASE) == []


def test_the_working_tree_holds_every_baseline_of_its_last_commit():
    """The command CI runs against the change's base, run here against HEAD: it reads both commits' own files,
    and an edit that loosens a baseline fails before it is committed."""
    head = ratchet.baselines(ratchet._at("HEAD", ratchet.MAP), ratchet._at("HEAD", ratchet.PYPROJECT))
    assert head["ceiling"] == 400 and head["ceilings"]
    assert ratchet.against("HEAD") == []
