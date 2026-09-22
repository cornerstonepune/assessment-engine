"""No promise without a command (goals/promises-kept.yaml).

ADR 0007 designed the reader's learning loop on 2026-09-19 and it sat unbuilt for three days: the goal
file held `correction_must_change_a_later_read: true`, a line that looked like a check and was run by
nothing. These rules make such a line impossible to write:

- a goal file holds only its sentence, Nimish's own words (`says`, each with the test that proves it),
  scenarios, criteria that are commands, and what is still `manual`. Any other key is refused.
- every `says` line names a test that exists: `path::test_name` for pytest, `path::test title` for the
  website's tests.
- a goal written from 2026-09-22 must carry `says`; the fourteen written before are grandfathered.
- a decision record from ADR 0032 on names the goal that proves it (`Goal: goals/x.yaml`), or says why
  it has none (`Goal: none — …`).
"""

import re

import yaml

from engine.core import db

ALLOWED = {"name", "goal", "says", "scenarios", "criteria", "manual"}
# The goals written before this rule (2026-09-22). They keep working; new ones must name their proofs.
GRANDFATHERED = {
    "s1-site-answers", "s2-skill-map-outcomes", "s3-worksheet-library", "s4-validation-queue",
    "s5-question-bank-explained", "s7-paper-from-library", "s8-every-skill-a-question-uses",
    "s8t-taxonomy-coverage", "s9-combined-questions", "s10-mixed-papers", "w1-build-the-bank",
    "w2-assemble-and-print", "w3-read-and-graph", "w4-close-the-loop",
}  # fmt: skip
FIRST_ADR_WITH_A_GOAL = 32


def test_exists(proved_by):
    """`path::name` → does that test exist? A pytest function by name, or a website test by its title."""
    if "::" not in proved_by:
        return False
    path, name = (x.strip() for x in proved_by.split("::", 1))
    f = db.REPO_ROOT / path
    if not f.exists():
        return False
    src = f.read_text()
    if f.suffix == ".py":
        return re.search(rf"^def {re.escape(name)}\(", src, re.M) is not None
    return re.search(r"test\(\s*[`\"']" + re.escape(name) + r"[`\"']", src) is not None


def goal_problems(path):
    spec = yaml.safe_load(path.read_text()) or {}
    out = [
        f"{path.name}: `{k}` is not a command, a sentence with its test, or a manual step"
        for k in sorted(set(spec) - ALLOWED)
    ]
    for c in spec.get("criteria") or []:
        if not (isinstance(c.get("run"), str) and c["run"].strip() and "expect" in c):
            out.append(
                f"{path.name}: criterion {c.get('name', '?')!r} has no command to run and nothing to expect"
            )
    says = spec.get("says") or []
    if path.stem not in GRANDFATHERED and not says:
        out.append(f"{path.name}: says none of Nimish's words, so nothing ties the goal to what he asked for")
    for s in says:
        if not s.get("words"):
            out.append(f"{path.name}: a `says` entry has no words")
        elif not test_exists(s.get("proved_by", "")):
            out.append(
                f"{path.name}: {s['words']!r} is proved by {s.get('proved_by')!r}, which is not a test that exists"
            )
    for m in spec.get("manual") or []:
        if not isinstance(m, str) or not m.strip():
            out.append(f"{path.name}: a manual step is not a sentence")
    return out


def adr_problems(path):
    n = int(path.name[:4])
    if n < FIRST_ADR_WITH_A_GOAL:
        return []
    m = re.search(r"^Goal: (.+)$", path.read_text(), re.M)
    if not m:
        return [f"{path.name}: names no goal (`Goal: goals/x.yaml`, or `Goal: none — why`)"]
    said = m.group(1).strip()
    if said.startswith("none"):
        return [] if "—" in said or "-" in said[4:] else [f"{path.name}: `Goal: none` without a reason"]
    return [] if (db.REPO_ROOT / said).exists() else [f"{path.name}: names {said}, which does not exist"]


def problems():
    goals = sorted((db.REPO_ROOT / "goals").glob("*.yaml"))
    adrs = sorted((db.REPO_ROOT / "docs" / "adr").glob("[0-9][0-9][0-9][0-9]-*.md"))
    return [p for g in goals for p in goal_problems(g)] + [p for a in adrs for p in adr_problems(a)]
