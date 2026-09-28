#!/usr/bin/env python3
"""Imports Cambridge Primary curriculum frameworks as statements for the curriculum crosswalk (ADR 0041): each
learning objective with its code, stage, strand, sub-strand, page and text, word for word.

The copies read are recorded in docs/crosswalk/sources.json with their address and fingerprint, and a copy whose
fingerprint differs is refused. Until the school's own copies come from the Cambridge School Support Hub, these are
copies of Cambridge's publications hosted by other schools (Nimish, 28 Sep: "start building ... even if they are not
from the Cambridge official website ... we can just compare once I have the real documents"). Every statement is
found again, word for word, on its page before anything is written. No model is called.

python3 research/crosswalk_cambridge.py      # exit 1 if a copy differs or a statement is not on its page
"""

import hashlib
import json
import re
import sys
from pathlib import Path

import pymupdf
from spine_sources import download, sha256

R = Path(__file__).resolve().parents[1]
DATA = R / "data/crosswalk_sources"
SOURCES = R / "docs/crosswalk/sources.json"
# Cambridge's words stay out of this public repository: they are copied for the school's own use only ("Registered
# centres are permitted to copy material from this booklet for their own internal use"). The tracked index keeps each
# statement's code, place and a fingerprint of its words; the words are rebuilt here from the recorded copy.
OUT = R / "docs/crosswalk/statements"
WORDS = R / "data/crosswalk_statements"
# a learning objective's code as printed: *3Rw.01 is stage 3, strand R, sub-strand w, objective 1; the asterisk marks
# "the same learning objective" appearing "in more than one stage" (English 0058, page 15). Science in Context has no
# sub-strand: 1SIC.01.
CODE = re.compile(r"(?:^|(?<=\s))•?\s*(\*?)(\d)([A-Z]+)([a-z]{0,2})\.(\d{2})\s+")
# page furniture, and the per-stage list of the ways of working (TWM.01 Specialising), recorded once from their own page
# a code as a plain reading of any page shows it, followed by its objective; not an example ("e.g. 5Bs.01")
PRINTED = re.compile(r"(?<!e\.g\.)[\s•*](\d[A-Z]+[a-z]{0,2}\.\d{2})(?=\s)")
FURNITURE = re.compile(
    r"Back to contents page|Curriculum Framework|^\d+$|www\.cambridgeinternational\.org|^Stage \d$|^•?\s*[A-Z]+\.\d{2}\s"
)


def joined(text):
    """A hyphen at the end of a line is the word's own ("non-fiction", "multi-clause"): keep it, drop the break."""
    return re.sub(r"-[ \t]*\n\s*", "-", text)


def norm(text):
    """Whitespace-insensitive text; Word's space before a comma or full stop after a fraction dropped."""
    return re.sub(r" ([,.;])", r"\1", " ".join(joined(text).split()))


def on(text, page_text):
    """Found word for word in a plain reading of the page, where a stacked fraction 1/2 reads as its two numbers."""
    return (
        norm(text) in page_text
        or norm(re.sub(r"(\d+)/(\d+)", r"\1 \2", text)) in page_text
    )


def fetch(source):
    """The copy the import read, downloaded if missing; refused if its fingerprint is not the recorded one."""
    path = DATA / source["file"]
    if not path.exists():
        DATA.mkdir(parents=True, exist_ok=True)
        path.write_bytes(download(source["url"]))
    if (got := sha256(path)) != source["sha256"]:
        raise SystemExit(
            f"{source['url']} is not the copy the import read (sha256 {got}): re-import and compare"
        )
    return path


def bold(span):
    return bool(span["flags"] & 16) or "Bold" in span["font"]


def stacked(a, b):
    """A fraction as Word sets it: a small numerator, then a small denominator straight below it."""
    small = [s["size"] < 9.5 and s["text"].strip().isdigit() for s in (a, b)]
    return (
        all(small)
        and abs(a["bbox"][0] - b["bbox"][0]) < 2
        and b["bbox"][1] > a["bbox"][1] + 4
    )


def spans_text(block):
    """A block's text, line by line, with a stacked fraction written 1/2 and a sub-list's "o" bullet written ◦."""
    # (span, whether it opens a line after the first)
    spans = [
        (s, j > 0 and i == 0)
        for j, line in enumerate(block["lines"])
        for i, s in enumerate(line["spans"])
    ]
    out, i = [], 0
    while i < len(spans):
        (s, new_line), nxt = spans[i], spans[i + 1][0] if i + 1 < len(spans) else None
        out.append("\n" if new_line else "")
        if nxt and stacked(s, nxt):
            out.append(f" {s['text'].strip()}/{nxt['text'].strip()} ")
            i += 2
            continue
        bullet = s["text"].strip() == "o" and "Courier" in s["font"]
        out.append("◦ " if bullet else s["text"])
        i += 1
    return "".join(out)


def titles(text, strands):
    """True for a strand's own title, or the titles of both columns in one line ("Reading Writing"): not a sub-strand."""
    for name in sorted(strands.values(), key=len, reverse=True):
        text = text.replace(name, "")
    return not text.strip()


def blocks(page):
    """(column, y, kind, text) for every block of a page: objectives (they start with a code), headings (all bold),
    and the rest, which continue the objective above them (a wrapped line, a sub-list)."""
    mid, out = page.rect.width / 2, []
    for block in page.get_text("dict")["blocks"]:
        spans = [
            s
            for line in block.get("lines", [])
            for s in line["spans"]
            if s["text"].strip()
        ]
        flat = " " + norm(spans_text(block)) if spans else ""
        if not flat.strip() or FURNITURE.search(flat.strip()):
            continue
        x0, y0, *_ = block["bbox"]
        kind = (
            "objective"
            if CODE.search(flat)
            else "heading"
            if all(map(bold, spans))
            else "more"
        )
        out.append((int(x0 > mid), y0, kind, flat))
    return out


def objectives(page, number, strands):
    """The learning objectives on one page, each under the nearest heading above it in its column, each with the
    wrapped lines and sub-list below it. Returns the rows, the notes set straight under a heading ("By end of Stage 4
    learners should have a secure understanding of phonics."), and any other text that follows no objective."""
    found, rows, notes, orphans = blocks(page), [], [], []
    for column, y0, kind, flat in found:
        if kind != "objective":
            continue
        above = [
            f
            for f in found
            if f[0] == column
            and f[1] < y0
            and f[2] == "heading"
            and not titles(f[3], strands)
        ]
        marks = list(CODE.finditer(flat))
        for m, nxt in zip(marks, marks[1:] + [None], strict=True):
            star, stage, strand, sub, n = m.groups()
            stem, *items = (
                flat[m.end() : nxt.start() if nxt else len(flat)]
                .removeprefix("•")
                .split("◦")
            )
            rows.append(
                {
                    "code": f"{stage}{strand}{sub}.{n}",
                    "repeats_across_stages": bool(star),
                    "stage": int(stage),
                    "strand": strands[strand],
                    "substrand_letter": sub,
                    "substrand": (
                        max(above, key=lambda h: h[1])[3].strip() if above else None
                    )
                    if sub
                    else strands[strand],
                    "text": stem.strip().removeprefix("•").strip(),
                    "items": [i.strip() for i in items],
                    "pdf_page": number,
                    "_at": (column, y0),
                }
            )
    for column, y0, kind, flat in found:
        if kind != "more":
            continue
        before = [r for r in rows if r["_at"][0] == column and r["_at"][1] < y0]
        if not before:
            above = [f for f in found if f[0] == column and f[1] < y0]
            head = max(above, key=lambda f: f[1]) if above else None
            if head and head[2] == "heading":
                notes.append(
                    {
                        "substrand": head[3].strip(),
                        "text": flat.strip(),
                        "pdf_page": number,
                    }
                )
            else:
                orphans.append(flat.strip())
            continue
        row = max(
            before, key=lambda r: r["_at"][1]
        )  # the last objective above: max keeps the first of equals
        row = [r for r in before if r["_at"] == row["_at"]][-1]
        if flat.strip().startswith("◦"):
            row["items"] += [i.strip() for i in flat.split("◦")[1:]]
        elif row["items"]:
            row["items"][-1] += " " + flat.strip()
        else:
            row["text"] += " " + flat.strip()
    stages = {r["stage"] for r in rows}
    for n in notes:
        n["stage"] = stages.pop() if len(stages) == 1 else None
    for r in rows:
        del r["_at"]
    return rows, notes, orphans


def characteristics(doc, spec, strands):
    """Ways of working that "apply to all of the primary stages" (maths: Thinking and Working Mathematically), each
    named and described once on one page; a statement with no stage."""
    flat = norm(doc[spec["pdf_page"] - 1].get_text())
    at = sorted(
        (flat.index(name + " "), code, name) for code, name in spec["names"].items()
    )
    ends = [a for a, *_ in at[1:]] + [flat.index(spec["ends"])]
    return [
        {
            "code": code,
            "repeats_across_stages": True,
            "stage": None,
            "strand": strands[spec["strand"]],
            "substrand_letter": "",
            "substrand": name,
            "text": flat[a + len(name) : end].strip(),
            "items": [],
            "pdf_page": spec["pdf_page"],
        }
        for (a, code, name), end in zip(at, ends, strict=True)
    ]


def read(source, path=None):
    """Every learning objective in one framework, checked word for word on its page: in the recorded copy, or in
    another file of the same framework (the official copy, to compare)."""
    doc = pymupdf.open(path or fetch(source))
    spec = source.get("characteristics")
    rows = characteristics(doc, spec, source["strands"]) if spec else []
    missing = [
        r["code"]
        for r in rows
        if not on(r["text"], norm(doc[r["pdf_page"] - 1].get_text()))
    ]
    orphans, notes, unread = [], [], []
    for i, page in enumerate(doc, 1):
        found, said, loose = objectives(page, i, source["strands"])
        # a note among the objectives, not the front matter
        notes += said if found else []
        on_page = norm(page.get_text())
        # every code a plain reading of the page shows, read by the parser: nothing on a page is skipped
        unread += sorted(set(PRINTED.findall(on_page)) - {r["code"] for r in found})
        missing += [
            r["code"]
            for r in found
            if not all(on(t, on_page) for t in [r["text"], *r["items"]])
        ]
        orphans += [f"p{i}: {t[:60]}" for t in loose] if found else []
        rows += found
    # a sub-strand keeps one name across stages; fill a gap from the same strand and letter elsewhere
    names = {}
    for r in rows:
        if r["substrand"]:
            names.setdefault((r["strand"], r["substrand_letter"]), r["substrand"])
    for r in rows:
        r["substrand"] = r["substrand"] or names.get(
            (r["strand"], r["substrand_letter"])
        )
    return rows, notes, missing, orphans + [f"not read: {c}" for c in unread]


def whole(row):
    """An objective as one sentence: its stem and, when it has one, its list."""
    return " ".join([row["text"], *row["items"]])


def fingerprint(row):
    """sha256 of a statement's words (stem and list), whitespace-insensitive: what the tracked index keeps."""
    words = " ".join([row["text"], *row.get("items", [])])  # a note has no list
    return hashlib.sha256(norm(words).encode()).hexdigest()


def index(row):
    """A statement as the public repository keeps it: everything but the words, and their fingerprint."""
    kept = {k: v for k, v in row.items() if k not in ("text", "items")}
    return {**kept, "items": len(row.get("items", [])), "text_sha256": fingerprint(row)}


def words(framework):
    """The statements of one framework with their words, as the importer read them into data/."""
    path = WORDS / f"{framework.lower()}.json"
    if not path.exists():
        raise SystemExit(
            f"{path.relative_to(R)} is missing: run python3 research/crosswalk_cambridge.py first"
        )
    return json.loads(path.read_text())


def main():
    sources = json.loads(SOURCES.read_text())
    OUT.mkdir(parents=True, exist_ok=True)
    WORDS.mkdir(parents=True, exist_ok=True)
    bad = False
    for source in sources:
        if source.get("reader") != "cambridge_primary":
            continue
        rows, notes, missing, orphans = read(source)
        codes = [r["code"] for r in rows]
        dupes = sorted({c for c in codes if codes.count(c) > 1})
        unnamed = sorted({r["code"] for r in rows if not r["substrand"]})
        unended = [
            r["code"]
            for r in rows
            if r["stage"] and not re.search(r"[.?!)”’\"…]$", whole(r))
        ]
        # a stem that introduces a list ("Understand addition as:") must have brought its list with it
        cut = [r["code"] for r in rows if r["text"].endswith(":") and not r["items"]]
        names = {}
        for r in rows:
            if r["stage"]:
                names.setdefault((r["strand"], r["substrand_letter"]), set()).add(
                    r["substrand"]
                )
        renamed = sorted(
            f"{k[0]} {k[1]}: {sorted(v)}" for k, v in names.items() if len(v) > 1
        )
        out = OUT / f"{source['framework'].lower()}.json"
        book = {
            "framework": source["framework"],
            "sha256": source["sha256"],
            "objectives": rows,
            "notes": notes,
        }
        (WORDS / out.name).write_text(
            json.dumps(book, ensure_ascii=False, indent=1) + "\n"
        )
        public = dict(
            book, objectives=[index(r) for r in rows], notes=[index(n) for n in notes]
        )
        out.write_text(json.dumps(public, ensure_ascii=False, indent=1) + "\n")
        stages = sorted({r["stage"] for r in rows if r["stage"]})
        print(
            f"{source['framework']}: {len(rows)} objectives, stages {stages}, "
            f"{len(rows) - len(missing)}/{len(rows)} found word for word on their page, {len(notes)} notes "
            f"-> {out.relative_to(R)}"
        )
        checks = (
            ("not on their page", missing),
            ("twice", dupes),
            ("no sub-strand", unnamed),
            ("a sub-strand letter with two names", renamed),
            ("a list introduced but not found", cut),
            ("text on an objectives page that follows no objective", orphans),
            ("not ending a sentence", unended),
        )
        for label, items in checks:
            if items:
                print(f"  {label}: {len(items)}, e.g. {items[:6]}")
        bad = bad or bool(missing or dupes or unnamed or renamed or cut or orphans)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
