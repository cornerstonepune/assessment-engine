"""The map and the code agree (goals/workflows-visible.yaml).

`workflows.json` at the top of the repository names every step of the agreed workflow, the files that
do it, and the only connections one workflow may make to another. These tests fail the day a file, a
connection, a command or a screen drifts from it — so the layout Nimish asked for ("independent
workflows which connect very well to each other") is held by a check, not by anyone remembering.
"""

import ast
import json
import pathlib

import pytest

ENGINE = pathlib.Path(__file__).resolve().parents[1]
REPO = ENGINE.parents[1]
WEB = REPO / "apps" / "web"
MAP = json.loads((REPO / "workflows.json").read_text())
STEPS = MAP["steps"]
FOLDERS = {w["folder"]: w["code"] for w in MAP["workflows"] if w["folder"]}
SHARED = {s["folder"]: s["code"] for s in MAP["shared"]}
LOWER = {"core", "assess", "adapters"}  # the layers every workflow may stand on


def engine_files():
    return sorted(
        str(p.relative_to(ENGINE))
        for p in (ENGINE / "engine").rglob("*.py")
        if p.name != "__init__.py" and "__pycache__" not in p.parts
    )


def part_of(path):
    """→ (kind, code) for an engine file: its workflow, or the shared part that holds it."""
    for folder, code in FOLDERS.items():
        if path.startswith(folder + "/"):
            return "workflow", code
    for s in MAP["shared"]:
        if path.startswith(s["folder"] + "/") or path in s.get("files", []):
            return "shared", s["code"]
    return None, None


def imports(path):
    """Every engine file this one imports, lazily or not."""
    tree = ast.parse((ENGINE / path).read_text())
    names = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom) and n.level == 0 and n.module and n.module.startswith("engine"):
            names |= {f"{n.module}.{a.name}" for a in n.names} | {n.module}
        elif isinstance(n, ast.Import):
            names |= {a.name for a in n.names if a.name.startswith("engine")}
    out = set()
    for name in names:
        rel = pathlib.Path(*name.split("."))
        for candidate in (rel.with_suffix(".py"), rel / "__init__.py"):
            if (ENGINE / candidate).exists() and candidate.name != "__init__.py":
                out.add(str(candidate))
    return out


def test_every_engine_file_belongs_to_exactly_one_part_of_the_map():
    listed = [f for s in STEPS for f in s["files"]]
    assert len(listed) == len(set(listed)), "a file is named by two steps"
    for f in listed:
        assert (ENGINE / f).exists(), f"the map names {f}, which does not exist"
    for f in engine_files():
        kind, code = part_of(f)
        assert kind, f"{f} is in no part of the map: add it to a step or a shared part of workflows.json"
        if kind == "workflow":
            steps = [s for s in STEPS if f in s["files"]]
            assert steps, f"{f} sits in {code}'s folder but no step of the map names it"
            assert steps[0]["workflow"] == code, (
                f"{f} sits in {code}'s folder but step {steps[0]['code']} is {steps[0]['workflow']}'s"
            )
        else:
            assert f not in listed, f"{f} is shared ({code}) but a step names it as its own"


def test_a_workflow_reaches_another_only_through_a_declared_hand_over():
    declared = {(h["from"], h["to"]) for h in MAP["handovers"]}
    used = set()
    for f in engine_files():
        kind, code = part_of(f)
        for g in imports(f):
            gkind, gcode = part_of(g)
            if kind == "workflow" and gkind == "workflow" and gcode != code:
                assert (f, g) in declared, (
                    f"{f} ({code}) reaches {g} ({gcode}) — not a hand-over the map declares"
                )
                used.add((f, g))
            if kind == "workflow" and gkind == "shared":
                assert gcode in LOWER, (
                    f"{f} ({code}) reaches {g} ({gcode}): a workflow stands on core, assess and adapters only"
                )
            if kind == "shared" and code in LOWER:
                assert gkind == "shared" and gcode in LOWER, (
                    f"{f} ({code}) reaches {g}: the base must not depend on a workflow or a door"
                )
            if code == "assess":
                assert gcode == "assess", f"{f} reaches {g}: the maths library is pure and stands alone"
    assert declared == used, f"hand-overs declared but never made: {sorted(declared - used)}"


def test_no_file_grows_past_the_ceiling():
    limit, frozen = MAP["ceilings"]["limit"], MAP["ceilings"]["frozen"]
    for f in engine_files():
        n = len((ENGINE / f).read_text().splitlines())
        ceiling = frozen.get(f, limit)
        assert n <= ceiling, (
            f"{f} has {n} lines; its ceiling is {ceiling} — split it along a real responsibility"
        )
    for f, ceiling in frozen.items():
        assert ceiling > limit, f"{f} is at or under {limit} lines now: take it off the frozen list"


def test_every_step_says_whether_it_works_for_any_subject():
    for part in [*STEPS, *MAP["shared"]]:
        subject = part.get("subject") or {}
        assert isinstance(subject.get("any"), bool), (
            f"{part['code']} does not say whether it works for any subject"
        )
        assert subject["any"] or subject.get("note"), (
            f"{part['code']} is maths only and does not say what a new subject needs"
        )
    for s in STEPS:
        assert s["built"] in ("live", "partly", "not built"), s["code"]
        if s["built"] == "not built":
            assert not s["files"], f"{s['code']} says not built but names files"
        else:
            assert s["files"] or s["screens"], f"{s['code']} says {s['built']} but names nothing that does it"
    codes = {s["code"] for s in STEPS}
    assert codes == {f"N{i}" for i in range(1, 13)}, (
        "the map holds the twelve agreed steps, no more and no fewer"
    )
    for w in MAP["workflows"]:
        assert {s["code"] for s in STEPS if s["workflow"] == w["code"]} == set(w["steps"]), w["code"]


def test_every_command_the_map_names_is_a_real_command():
    import typer

    from engine.cli import app

    root = typer.main.get_command(app)
    for s in STEPS:
        for cmd in s["commands"]:
            node = root
            for w in cmd.split()[1:]:
                assert w in getattr(node, "commands", {}), (
                    f"{s['code']} names `{cmd}`, which is not a command"
                )
                node = node.commands[w]


@pytest.mark.skipif(not WEB.exists(), reason="the website is not beside the engine here")
def test_every_screen_the_map_names_exists():
    routes = {
        "/"
        + "/".join(p.relative_to(WEB / "app").parts[:-1])
        .replace("(app)/", "")
        .replace("(app)", "")
        .strip("/")
        for p in (WEB / "app").rglob("*")
        if p.name in ("page.tsx", "route.ts")
    }
    routes = {r.rstrip("/") or "/" for r in routes}
    for s in STEPS:
        for screen in s["screens"]:
            assert screen in routes, f"{s['code']} names the screen {screen}, which the website does not have"


def test_every_engine_import_in_a_shell_script_resolves():
    """The Python inside `deploy/` and `bin/` is run only on the day it is needed; a module moved in the engine
    must fail here, not halfway through going live (2026-09-23: go-live stopped on `from engine import db`)."""
    import importlib
    import re

    found = []
    for script in [*(REPO / "deploy").glob("*.sh"), *(p for p in (REPO / "bin").iterdir() if p.is_file())]:
        for m in re.finditer(r"^\s*from (engine[\w.]*) import ([\w, ]+)$", script.read_text(), re.M):
            mod = importlib.import_module(m[1])
            for name in (n.strip() for n in m[2].split(",")):
                found.append((script.name, name))
                assert hasattr(mod, name) or importlib.util.find_spec(f"{m[1]}.{name}"), (
                    f"{script.relative_to(REPO)}: `from {m[1]} import {name}` does not resolve"
                )
    assert found, "no shell script imports the engine; this check reads nothing"
