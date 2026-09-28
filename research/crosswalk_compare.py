#!/usr/bin/env python3
"""Compares a Cambridge framework as the school receives it (the official copy from the School Support Hub) with the
copy the crosswalk was built from, objective by objective, by code. Nimish, 28 Sep: "Once I have that, we can just
compare once I have the real documents also". The file says which framework it is on its first page (0096 Maths,
0058 English, 0097 Science). It is read by the same reader and checked word for word on its own pages, and what
differs is listed. Nothing in the crosswalk changes until a person has looked. The report holds Cambridge's words, so
it is written under data/, which is never committed: the repository is public.

~/cornerstone/assessment-engine/bin/compare-cambridge ~/Downloads/<official framework>.pdf [more files …]
"""

import json
import re
import sys
from pathlib import Path

import pymupdf
from crosswalk_cambridge import SOURCES, WORDS, norm, read, whole, words

R = Path(__file__).resolve().parents[1]
OUT = R / "data/crosswalk_compare"


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


def which(first_pages, sources):
    """The framework a file is, from the syllabus number and title its first pages print ("Cambridge Primary
    Mathematics 0096"): exactly one Cambridge Primary source must match, or None."""
    text = " ".join(first_pages.split())
    hits = [
        s
        for s in sources
        if s.get("reader") == "cambridge_primary"
        and re.search(rf"\b{s['framework'][-4:]}\b", text)
        and s["name"].split(" 0")[0] in text
    ]
    return hits[0] if len(hits) == 1 else None


def copy_of(source):
    """The copy's statements with their words: from data/ when this machine has built them, else read again from the
    recorded copy, which is downloaded and checked against its fingerprint."""
    if (WORDS / f"{source['framework'].lower()}.json").exists():
        return words(source["framework"])["objectives"]
    rows, _, missing, orphans = read(source)
    if missing or orphans:
        raise SystemExit(
            f"{source['framework']}: the recorded copy did not read cleanly"
        )
    return rows


def one(path, sources):
    doc = pymupdf.open(path)
    source = which(
        " ".join(doc[i].get_text() for i in range(min(2, len(doc)))), sources
    )
    if source is None:
        print(
            f"{path.name}: not one of the Cambridge Primary frameworks in {SOURCES.relative_to(R)}"
        )
        return 2
    official, _, missing, orphans = read(source, path)
    if missing or orphans:
        print(
            f"{path.name}: did not read cleanly ({len(missing)} statements not found on their page, "
            f"{len(orphans)} lines that follow no objective); the layout may differ from the copy's"
        )
        return 1
    diff = compare(copy_of(source), official)
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / f"{source['framework'].lower()}.json"
    report = {"framework": source["framework"], "official": str(path), **diff}
    out.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n")
    print(
        f"{source['framework']} ({path.name}): {len(diff['same'])} the same, {len(diff['changed'])} changed, "
        f"{len(diff['only_in_copy'])} only in our copy, {len(diff['only_in_official'])} only in the official file"
    )
    for label, codes in (
        ("changed", [c["code"] for c in diff["changed"]]),
        ("only in our copy", diff["only_in_copy"]),
        ("only in the official file", diff["only_in_official"]),
    ):
        if codes:
            print(
                f"  {label}: {', '.join(codes[:20])}{' …' if len(codes) > 20 else ''}"
            )
    print(f"  the words, side by side: {out.relative_to(R)}")
    return 0


def main(argv):
    if not argv:
        print(__doc__.strip().splitlines()[-1])
        return 2
    sources = json.loads(SOURCES.read_text())
    return max(one(Path(a).expanduser(), sources) for a in argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
