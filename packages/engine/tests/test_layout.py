"""The map and the code agree (goals/workflows-visible.yaml).

`workflows.json` at the top of the repository names every step of the agreed workflow, the files that
do it, and the only connections one workflow may make to another. These tests fail the day a file, a
connection, a command or a screen drifts from it — so the layout Nimish asked for ("independent
workflows which connect very well to each other") is held by a check, not by anyone remembering.
"""

import ast
import json
import pathlib
import re
import subprocess
import sys

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


def web_files():
    """The website's own code — pages, components, queries, browser tests, its config — as `apps/web/…`; never
    what a build or a test run writes."""
    own = [p for d in ("app", "lib", "components", "tests") for p in (WEB / d).rglob("*")]
    own += [p for p in WEB.iterdir() if p.name != "next-env.d.ts"]
    return sorted(str(p.relative_to(REPO)) for p in own if p.suffix in {".ts", ".tsx", ".js", ".mjs"})


def sized_files():
    """{file: lines} for every file the ceiling covers (`ceilings.covers`): the engine's, and the website's."""
    covers = MAP["ceilings"]["covers"]
    sizes = {f: len((ENGINE / f).read_text().splitlines()) for f in engine_files()}
    sizes |= {f: len((REPO / f).read_text().splitlines()) for f in web_files()}
    return {f: n for f, n in sizes.items() if f.startswith(tuple(covers))}


def test_no_file_grows_past_the_ceiling():
    limit, frozen = MAP["ceilings"]["limit"], MAP["ceilings"]["frozen"]
    sized = sized_files()
    for f, n in sized.items():
        ceiling = frozen.get(f, limit)
        assert n <= ceiling, (
            f"{f} has {n} lines; its ceiling is {ceiling} — split it along a real responsibility"
        )
    for f, ceiling in frozen.items():
        assert ceiling > limit, f"{f} is at or under {limit} lines now: take it off the frozen list"
        # a frozen file that shrank writes its new size down, or it could grow back to the old one unseen
        assert sized.get(f) == ceiling, (
            f"{f} has {sized.get(f)} lines, not its frozen {ceiling}: write {sized.get(f)}"
        )


def test_the_ceiling_holds_the_website_too():
    """The 400 lines held the engine alone; a page or a browser test could grow without end (code review,
    2026-09-30; goals/p1-the-gates-hold.yaml)."""
    sized = sized_files()
    assert "apps/web/lib/maker.ts" in sized and "apps/web/tests/e2e.spec.ts" in sized
    assert not [f for f in sized if "/.next" in f or "node_modules" in f or "test-results" in f]


def complexity():
    """{"file::function": {rule: measure}} for every function ruff finds past the map's limits: C901, the
    branches a reader must hold at once, and PLR0915, the statements in one function."""
    limit = MAP["complexity"]["limit"]
    found = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "engine", "tests", "--select", ",".join(limit),
         "--config", f"lint.mccabe.max-complexity={limit['C901']}",
         "--config", f"lint.pylint.max-statements={limit['PLR0915']}",
         "--output-format", "json", "--exit-zero"],
        cwd=ENGINE, capture_output=True, text=True, check=True,
    ).stdout  # fmt: skip
    out = {}
    for v in json.loads(found):
        path = pathlib.Path(v["filename"])
        (name,) = [
            n.name
            for n in ast.walk(ast.parse(path.read_text()))
            if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef) and n.lineno == v["location"]["row"]
        ]
        measure = int(re.search(r"\((\d+) > \d+\)", v["message"]).group(1))
        out.setdefault(f"{path.relative_to(ENGINE)}::{name}", {})[v["code"]] = measure
    return out


def test_no_function_grows_more_complex_than_the_map_allows():
    """A function past the limits is split, or frozen in the map at today's measure, where it may only shrink;
    ruff measured 30 past them on 2026-10-01 (goals/p1-the-gates-hold.yaml)."""
    limit, frozen = MAP["complexity"]["limit"], MAP["complexity"]["frozen"]
    found = complexity()
    for fn, measures in found.items():
        for rule, n in measures.items():
            allowed = frozen.get(fn, {}).get(rule, limit[rule])
            assert n <= allowed, (
                f"{fn} measures {rule} {n}, past {allowed}: split it along a real responsibility"
            )
    for fn, measures in frozen.items():
        for rule, n in measures.items():
            assert rule in found.get(fn, {}), (
                f"{fn} is within the {rule} limit now: take it off the frozen list"
            )
            # a function that shrank writes its new measure down, or it could grow back unseen
            assert found[fn][rule] == n, (
                f"{fn} measures {rule} {found[fn][rule]}, not its frozen {n}: write it"
            )


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
