"""The baselines only tighten (goals/p1-the-gates-hold.yaml).

Today's debt is written down and frozen: files over the 400-line ceiling at their size, functions past the
complexity limits at theirs (`workflows.json`), and the engine's coverage at its floor (`pyproject.toml`). A
test holds the code to each number; this holds the numbers to the commit before. A frozen file or function
may shrink and must never grow, nothing new joins a frozen list, no limit rises, nothing measured stops being
measured, and the coverage floor never falls. CI runs it against the base of every change (`engine ratchet
--base <commit>`), so "raise the limit" is a red build, not a quiet edit (CLAUDE.md rule 14).

A baseline written for the first time is today's debt being recorded, not a loosening: a file under a root the
ceiling did not cover before, and the complexity list on the commit that introduces it.
"""

import json
import subprocess
import tomllib

from engine.core import db

MAP = "workflows.json"
PYPROJECT = "packages/engine/pyproject.toml"


def baselines(map_text: str, pyproject_text: str) -> dict:
    """The numbers a commit holds itself to, from its own `workflows.json` and `pyproject.toml`."""
    m = json.loads(map_text)
    report = tomllib.loads(pyproject_text).get("tool", {}).get("coverage", {}).get("report", {})
    return {
        "ceiling": m["ceilings"]["limit"],
        # before the website was measured, the ceiling held the engine's own files alone
        "covers": m["ceilings"].get("covers", ["engine/"]),
        "ceilings": m["ceilings"]["frozen"],
        "complexity": m.get("complexity"),
        "coverage": float(report.get("fail_under", 0)),
    }


def _ceilings(base: dict, head: dict) -> list[str]:
    out = []
    if head["ceiling"] > base["ceiling"]:
        out.append(f"the line ceiling rose from {base['ceiling']} to {head['ceiling']}")
    out += [f"the ceiling no longer measures {root}" for root in base["covers"] if root not in head["covers"]]
    for f, n in head["ceilings"].items():
        if f in base["ceilings"]:
            if n > base["ceilings"][f]:
                out.append(f"{f} may have {n} lines, up from {base['ceilings'][f]}")
        elif f.startswith(tuple(base["covers"])):
            out.append(f"{f} joined the frozen files at {n} lines: split it instead")
    return out


def _complexity(base: dict | None, head: dict | None) -> list[str]:
    if base is None:
        return []  # the list is being written down on this commit
    if head is None:
        return ["the complexity limits are gone from the map"]
    out = []
    for rule, n in head["limit"].items():
        if n > base["limit"].get(rule, n):
            out.append(f"the {rule} limit rose from {base['limit'][rule]} to {n}")
    for fn, values in head["frozen"].items():
        if fn not in base["frozen"]:
            out.append(f"{fn} joined the frozen functions: split it instead")
            continue
        for rule, n in values.items():
            was = base["frozen"][fn].get(rule)
            if was is None:
                out.append(f"{fn} is newly allowed past the {rule} limit")
            elif n > was:
                out.append(f"{fn} may reach {rule} {n}, up from {was}")
    return out


def loosened(base: dict, head: dict) -> list[str]:
    """Every way `head` asks less of the code than `base` did; none is the only passing answer."""
    out = _ceilings(base, head) + _complexity(base["complexity"], head["complexity"])
    if head["coverage"] < base["coverage"]:
        out.append(f"the coverage floor fell from {base['coverage']:g}% to {head['coverage']:g}%")
    return out


def _at(ref: str, path: str) -> str:
    return subprocess.run(
        ["git", "show", f"{ref}:{path}"], cwd=db.REPO_ROOT, capture_output=True, text=True, check=True
    ).stdout


def against(ref: str) -> list[str]:
    """How this checkout's baselines compare with commit `ref`'s."""
    base = baselines(_at(ref, MAP), _at(ref, PYPROJECT))
    head = baselines((db.REPO_ROOT / MAP).read_text(), (db.REPO_ROOT / PYPROJECT).read_text())
    return loosened(base, head)
