"""The documents in hand, read as ADR 0041's zone 1 (what others say): NCF-SE 2023 and NCERT's learning outcomes
from the publisher's own files, and the Cambridge Primary frameworks from the copies recorded in
docs/crosswalk/sources.json. Each framework, the document the import read, its levels with the ages it prints (or how
they were worked out), and its statements word for word with their PDF page. Used by research/crosswalk_build.py.
"""

import datetime
import json
from pathlib import Path

import pymupdf
from crosswalk_cambridge import fetch as fetch_copy
from crosswalk_cambridge import fingerprint, words
from spine_sources import DATA as SPINE_DATA
from spine_verify import norm as spine_norm

R = Path(__file__).resolve().parents[1]
CW = R / "docs/crosswalk"
SPINE = R / "docs/spine/sources"
# when the publisher's files were first fetched for the spine (docs/spine/sources/official_documents.json has no date)
RETRIEVED = {
    "ncf": {"retrieved_at": "2026-09-27T13:26:30+00:00"},
    "elementary": {"retrieved_at": "2026-09-27T13:26:36+00:00"},
    "secondary": {"retrieved_at": "2026-09-27T13:26:39+00:00"},
}
NCF_STAGES = [  # as printed, NCF-SE 2023 page 62; the ages are the framework's own
    ("foundational", "Foundational", 3, 8),
    ("preparatory", "Preparatory", 8, 11),
    ("middle", "Middle", 11, 14),
    ("secondary", "Secondary", 14, 18),
]
NCF_AGES = (
    "Foundational Stage (in two parts, that is 3 years of Anganbadi or pre-school + 2 years in primary school in "
    "Grades 1–2; both together covering ages 3–8), Preparatory Stage (Grades 3–5, covering ages 8–11), Middle Stage "
    "(Grades 6–8, covering ages 11–14), and Secondary Stage (Grades 9–12 in two phases, i.e., 9 and 10 in the first "
    "and 11 and 12 in the second, covering ages 14–18)"
)
KINDS = {"CG": "curricular_goal", "C": "competency"}


def stamp(record, path):
    """When the copy was retrieved: as recorded, or, the first time, the moment the copy on disk was saved."""
    return record.get("retrieved_at") or datetime.datetime.fromtimestamp(
        path.stat().st_mtime, datetime.UTC
    ).isoformat(timespec="seconds")


def official_frameworks(docs):
    """NCF-SE and NCERT: the framework, the document the import read, and the levels with their ages."""
    by = {d["key"]: d for d in docs}
    names = {
        "ncf": "NCF-SE-2023",
        "elementary": "NCERT-LO-2017",
        "secondary": "NCERT-LO-2019",
    }
    frameworks, documents = [], []
    for key, code in names.items():
        d = by[key]
        frameworks.append(
            {
                "code": code,
                "name": d["title"],
                "publisher": d["publisher"],
                "kind": "national",
                "edition": d["edition"],
            }
        )
        documents.append(
            {
                "framework_code": code,
                "url": d["url"],
                "sha256": d["sha256"],
                "bytes": d["bytes"],
                "provenance": "publisher",
                "reading": d["read_as"],
                "retrieved_at": stamp(
                    RETRIEVED.get(key, {}), SPINE_DATA / f"{key}.pdf"
                ),
            }
        )
    return frameworks, documents


def official_levels(design):
    """NCF-SE's stages with the ages it prints; NCERT's classes at the ages NCF-SE gives their grades."""
    levels = [
        {
            "framework_code": "NCF-SE-2023",
            "code": name,
            "ord": i,
            "age_from": a,
            "age_to": b,
            "age_basis": "printed",
            "quote": NCF_AGES,
            "pdf_page": 62,
        }
        for i, (_, name, a, b) in enumerate(NCF_STAGES, 1)
    ]
    first = design["grade_age"]["grade_1_from"]
    for code, classes in (
        ("NCERT-LO-2017", range(1, 9)),
        ("NCERT-LO-2019", range(9, 11)),
    ):
        levels += [
            {
                "framework_code": code,
                "code": f"Class {g}",
                "ord": g,
                "age_from": first + g - 1,
                "age_to": first + g,
                "age_basis": "worked out: " + design["grade_age"]["rule"],
                "quote": NCF_AGES,
                "pdf_page": 62,
            }
            for g in classes
        ]
    return levels


def ncf_pages(rows):
    """The PDF page of each NCF-SE statement: the page on which its whole text is found, word for word."""
    doc = pymupdf.open(SPINE_DATA / "ncf.pdf")
    pages = [spine_norm(p.get_text()) for p in doc]
    found = {}
    for r in rows:
        text = spine_norm(r.get("text_full", r["text"]))
        hits = [i for i, p in enumerate(pages, 1) if text in p]
        found[r["id"]] = hits[0] if hits else None
    return found


def official_statements():
    ncf = json.loads((SPINE / "ncf_se_2023_competencies.json").read_text())
    ncert = json.loads((SPINE / "ncert_learning_outcomes.json").read_text())
    pages = ncf_pages(ncf)
    stage = {key: name for key, name, *_ in NCF_STAGES}
    rows = [
        {
            "framework_code": "NCF-SE-2023",
            "code": r["id"],
            "printed_code": r["code"],
            "parent_code": r.get("cg"),
            "level_code": stage[r["stage"]],
            "kind": KINDS[r["kind"]],
            "area": " · ".join(x for x in (r["subject"], r.get("area")) if x),
            "text": r.get("text_full", r["text"]),
            "items": [],
            "pdf_page": pages[r["id"]],
        }
        for r in ncf
    ]
    rows += [
        {
            "framework_code": "NCERT-LO-2017" if r["class"] <= 8 else "NCERT-LO-2019",
            "code": r["id"],
            "printed_code": None,
            "parent_code": None,
            "level_code": f"Class {r['class']}",
            "kind": "learning_outcome",
            "area": r["subject"],
            "text": r["text"],
            "items": [],
            "pdf_page": r["page"],
        }
        for r in ncert
    ]
    return rows


def cambridge(sources):
    """Each Cambridge framework read by research/crosswalk_cambridge.py: the framework, its copy, its six stages at
    the ages worked out from the range it prints, and its statements under their strands and sub-strands."""
    frameworks, documents, levels, rows = [], [], [], []
    for s in sources:
        if s.get("reader") != "cambridge_primary":
            continue
        code, ages = s["framework"], s["ages"]
        frameworks.append(
            {
                "code": code,
                "name": s["name"],
                "publisher": s["publisher"],
                "kind": "international",
                "edition": s["edition"],
                "text_in_repo": False,  # Cambridge's words are for the school's own use, not this public repository
            }
        )
        documents.append(
            {
                "framework_code": code,
                "url": s["url"],
                "sha256": s["sha256"],
                "bytes": s["bytes"],
                "provenance": "third_party_copy"
                if s["kind"] == "copy"
                else "publisher",
                "reading": f"PyMuPDF {pymupdf.VersionBind}: text spans by block; a stacked fraction as a/b; "
                "research/crosswalk_cambridge.py",
                "retrieved_at": stamp(s, fetch_copy(s)),
            }
        )
        stages = range(1, 7)
        span, rest = divmod(
            ages["to"] - ages["from"], len(stages)
        )  # one year a stage: 5 to 11 over six stages
        if rest:
            raise SystemExit(
                f"{code}: {len(stages)} stages do not divide the ages {ages['from']} to {ages['to']}"
            )
        levels += [
            {
                "framework_code": code,
                "code": f"Stage {n}",
                "ord": n,
                "age_from": ages["from"] + span * (n - 1),
                "age_to": ages["from"] + span * n,
                "age_basis": "worked out: six stages over the ages printed, one year each; Cambridge prints the range, "
                "not an age per stage",
                "quote": ages["quote"],
                "pdf_page": ages["pdf_page"],
            }
            for n in stages
        ]
        rows += cambridge_statements(s)
    return frameworks, documents, levels, rows


def cambridge_statements(source):
    book = words(source["framework"])
    tracked = json.loads(
        (CW / "statements" / f"{source['framework'].lower()}.json").read_text()
    )
    kept = {r["code"]: r["text_sha256"] for r in tracked["objectives"]}
    changed = [
        o["code"] for o in book["objectives"] if kept.get(o["code"]) != fingerprint(o)
    ]
    if changed:
        raise SystemExit(
            f"{source['framework']}: the words in data/ are not the ones the index records: {changed[:5]}"
        )
    code, letters = source["framework"], {v: k for k, v in source["strands"].items()}
    rows, parents = [], {}
    for o in book["objectives"]:
        strand = letters[o["strand"]]
        sub = strand + o["substrand_letter"] if o["substrand_letter"] else None
        for key, kind, text, parent in (
            (strand, "strand", o["strand"], None),
            (sub, "substrand", o["substrand"], strand),
        ):
            if key and key not in parents:
                parents[key] = o["pdf_page"]
                rows.append(
                    {
                        "framework_code": code,
                        "code": key,
                        "printed_code": key,
                        "parent_code": parent,
                        "level_code": None,
                        "kind": kind,
                        "area": o["strand"],
                        "text": text,
                        "items": [],
                        "pdf_page": o["pdf_page"],
                    }
                )
        rows.append(
            {
                "framework_code": code,
                "code": o["code"],
                "printed_code": (
                    "*" if o["repeats_across_stages"] and o["stage"] else ""
                )
                + o["code"],
                "parent_code": sub or strand,
                "level_code": f"Stage {o['stage']}" if o["stage"] else None,
                "kind": "learning_objective" if o["stage"] else "characteristic",
                "area": " · ".join(dict.fromkeys([o["strand"], o["substrand"]])),
                "text": o["text"],
                "items": o["items"],
                "pdf_page": o["pdf_page"],
            }
        )
    for i, n in enumerate(book["notes"], 1):
        rows.append(
            {
                "framework_code": code,
                "code": f"note.{n['stage']}.{i}",
                "printed_code": None,
                "parent_code": next(
                    (
                        r["code"]
                        for r in rows
                        if r["kind"] == "substrand" and r["text"] == n["substrand"]
                    ),
                    None,
                ),
                "level_code": f"Stage {n['stage']}" if n["stage"] else None,
                "kind": "note",
                "area": n["substrand"],
                "text": n["text"],
                "items": [],
                "pdf_page": n["pdf_page"],
            }
        )
    return rows
