"""A goal is a sentence plus the commands that prove it. `engine goal <name>`.

Nimish, 2026-09-20: "we need to start having a very specific goal for every task/milestone and have
very specific tests to prove that goal, and the system needs to keep working till the goal is
achieved." `BUILD-ORDER.md` had the goals as prose and the proofs as commands someone had to
remember to run. A goal file makes them one runnable thing, so "is it done?" is never an opinion.

A criterion passes when its command exits 0 and its output contains `expect`. Nothing here knows
anything about this project — the goals live in `goals/*.yaml`, as rows of a kind (rule 1).
"""

import os
import subprocess
import sys

import yaml

from engine import db

GOALS = db.REPO_ROOT / "goals"


def names():
    return sorted(p.stem for p in GOALS.glob("*.yaml"))


def load(name):
    path = GOALS / f"{name}.yaml"
    if not path.exists():
        raise ValueError(f"no goal {name!r} in goals/ — have {', '.join(names()) or 'none'}")
    spec = yaml.safe_load(path.read_text())
    for field in ("name", "goal", "criteria"):
        if field not in spec:
            raise ValueError(f"{path.name} has no {field!r}")
    return spec


def scenarios_of(spec):
    """The functional half of a goal: real requests, each with its own pass/fail."""
    return spec.get("scenarios") or []


def check(name, timeout=1800):
    """Run every criterion in order. Returns (spec, [(criterion, passed, output)])."""
    spec = load(name)
    # The engine's own console script, so a goal file writes `engine ...` and never a path.
    env = {**os.environ, "PATH": f"{os.path.dirname(sys.executable)}{os.pathsep}{os.environ.get('PATH', '')}"}
    results = []
    for c in spec["criteria"]:
        try:
            p = subprocess.run(
                c["run"],
                shell=True,
                cwd=db.REPO_ROOT,
                env=env,
                timeout=timeout,
                capture_output=True,
                text=True,
            )
            out = (p.stdout or "") + (p.stderr or "")
            ok = p.returncode == 0 and (c.get("expect", "") in out)
        except subprocess.TimeoutExpired:
            out, ok = f"timed out after {timeout}s", False
        results.append((c, ok, out))
    return spec, results
