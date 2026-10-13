"""M5e: the files each multiplication and division slice changed, per part of the map (BUILD-ORDER: "The score is the
files each slice changed, per workflow, recorded in STATE.md at M5").

A slice is the name a commit's title starts with — `M0a`, `M4d2b5`, `M5b` — as every commit of the × ÷ build is titled;
its record and its measurement count as its own (`M4c's record`). A file is placed by `workflows.json`: a workflow by its
folder, a shared part by its folder or its own files; beside them the website, the rows the loader reads, the schema,
the tests and the docs. A file a slice changed twice counts once."""

import json
import re
import subprocess
from collections import Counter
from collections.abc import Callable

from engine.core import db

SLICE = re.compile(r"^(M\d[a-z0-9]*)\b")
# every part a file is placed in, in the order the score prints them: the workflows, what they stand on, the rest
PARTS = "W1 W2 W3 W4 assess core adapters checks doors website rows schema map tests research ci docs other".split()
ENGINE = "packages/engine/"
# the parts outside the engine's code, by where their files live; the first that holds a path places it
AROUND = (
    ("packages/engine/tests/", "tests"),
    ("apps/web/tests/", "tests"),
    ("apps/web/", "website"),
    ("supabase/seed/", "rows"),
    ("supabase/migrations/", "schema"),
    ("workflows.json", "map"),
    ("research/", "research"),
    (".github/", "ci"),
    ("goals/", "docs"),
    ("docs/", "docs"),
)


def placer(map_text: str | None = None) -> Callable[[str], str]:
    """→ place(path): the part of the map a repository path belongs to."""
    m = json.loads(map_text or (db.REPO_ROOT / "workflows.json").read_text())
    folders = [(w["folder"] + "/", w["code"]) for w in m["workflows"] if w["folder"]]
    shared = [(s["folder"] + "/", s["code"]) for s in m["shared"]]
    own = {f: s["code"] for s in m["shared"] for f in s.get("files", [])}

    def place(path: str) -> str:
        for where, part in AROUND:
            if path.startswith(where):
                return part
        if path.endswith(".md"):
            return "docs"
        if path.startswith(ENGINE):
            inner = path[len(ENGINE) :]
            if inner in own:
                return own[inner]
            for folder, code in folders + shared:
                if inner.startswith(folder):
                    return code
        return "other"

    return place


def changed(log: str) -> dict[str, set[str]]:
    """{slice: every file its commits changed}, from `git log --name-only --format=%x1e%s` (a record a commit)."""
    out: dict[str, set[str]] = {}
    for record in log.split("\x1e"):
        lines = [x for x in record.splitlines() if x.strip()]
        if lines and (m := SLICE.match(lines[0])):
            out.setdefault(m.group(1), set()).update(lines[1:])
    return out


def score(by_slice: dict[str, set[str]], place: Callable[[str], str]) -> list[dict]:
    """One row a slice, in the order built (their names sort so): its files counted per part."""
    return [
        {"slice": s, "files": len(files), "parts": dict(Counter(place(f) for f in sorted(files)))}
        for s, files in sorted(by_slice.items())
    ]


def of(ref: str = "HEAD") -> list[dict]:
    """The score of every × ÷ slice on `ref`'s history, merges left out: each squash-merged slice is its own commit."""
    log = subprocess.run(
        ["git", "log", ref, "--no-merges", "--name-only", "--format=%x1e%s"],
        cwd=db.REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return score(changed(log), placer())
