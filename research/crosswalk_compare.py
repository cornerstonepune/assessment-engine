#!/usr/bin/env python3
"""Compares a Cambridge framework as the school receives it (the official copy from the School Support Hub) with the
copy the crosswalk was built from, objective by objective, by code. Nimish, 28 Sep: "Once I have that, we can just
compare once I have the real documents also". The official file is read by the same reader and checked word for word
on its own pages; what differs is listed, and nothing in the crosswalk changes until a person has looked.

python3 research/crosswalk_compare.py CAM-PRI-MAT-0096 ~/Downloads/0096_Mathematics_Curriculum_Framework.pdf
"""

import json
import sys
from pathlib import Path

from crosswalk_cambridge import SOURCES, norm, read, whole, words

R = Path(__file__).resolve().parents[1]


def compare(copy, official):
    """{same, changed, only_in_copy, only_in_official} between two lists of statements, matched by code."""
    a = {r["code"]: norm(whole(r)) for r in copy}
    b = {r["code"]: norm(whole(r)) for r in official}
    return {
        "same": sorted(c for c in a.keys() & b.keys() if a[c] == b[c]),
        "changed": [
            {"code": c, "copy": a[c], "official": b[c]}
            for c in sorted(a.keys() & b.keys())
            if a[c] != b[c]
        ],
        "only_in_copy": sorted(a.keys() - b.keys()),
        "only_in_official": sorted(b.keys() - a.keys()),
    }


def main(argv):
    if len(argv) != 2:
        print(__doc__.strip().splitlines()[-1])
        return 2
    framework, path = argv
    source = next(
        (s for s in json.loads(SOURCES.read_text()) if s["framework"] == framework),
        None,
    )
    if source is None or source.get("reader") != "cambridge_primary":
        print(
            f"{framework}: not a Cambridge Primary framework in {SOURCES.relative_to(R)}"
        )
        return 2
    official, _, missing, orphans = read(source, Path(path).expanduser())
    if missing or orphans:
        print(
            f"the official file did not read cleanly: {len(missing)} statements not on their page, {len(orphans)} loose"
        )
        return 1
    copy = words(framework)["objectives"]
    diff = compare(copy, official)
    out = R / "docs/crosswalk/compare" / f"{framework.lower()}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            {"framework": framework, "official": str(path), **diff},
            ensure_ascii=False,
            indent=1,
        )
        + "\n"
    )
    print(
        f"{framework}: {len(diff['same'])} the same, {len(diff['changed'])} changed, "
        f"{len(diff['only_in_copy'])} only in the copy, {len(diff['only_in_official'])} only in the official file "
        f"-> {out.relative_to(R)}"
    )
    return (
        0
        if not (diff["changed"] or diff["only_in_copy"] or diff["only_in_official"])
        else 1
    )


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
