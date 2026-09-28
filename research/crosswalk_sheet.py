#!/usr/bin/env python3
"""The approval sheet for one drafted step, as the one table a CSV upload turns into a Google Sheet (ADR 0041).

Nimish, 28 Sep: "no approver needs to actually write" and "a sample which you can send to Akanksha, which becomes an
approval mechanism". So the sheet asks only for a decision on each row, Approve, Change or Reject, and a comment when
she wants one. The row ids and the claims each stands for are kept in docs/crosswalk/review/, so a sheet returned any
day is read back by research/crosswalk_decisions.py.

python3 research/crosswalk_sheet.py MATH.NUMBER.8       # data/crosswalk_review/<step>.csv
"""

import json
import re
import sys

from crosswalk_review import CW, OUT, R, load, rows, slug, whole

HEADER = [
    "Row",
    "Section",
    "Code",
    "The school's title, or the part",
    "What we say (draft)",
    "What NCF-SE says",
    "What Cambridge says",
    "What NCERT says",
    "Builds",
    "Tested by the engine's skill sets",
    "Notes",
    "Decision",
    "Comment",
]


def table(step):
    """The whole sample as one table, the way a plain CSV upload becomes a one-tab Google Sheet: the read-me lines
    first, then one header, then every row to decide."""
    t = load()
    objectives, rubric, uncovered = rows(t, step, brief=True)
    first = json.loads((CW / "drafts" / f"{slug(step)}.json").read_text()).get(
        "review_first"
    )
    if first:  # the first round: a sample chosen so that every part of the method shows
        objectives = [r for r in objectives if r["cells"][0] in first["objectives"]]
        uncovered = [
            r
            for r in uncovered
            if r["cells"][0].split(" ")[0]
            in {
                c.split(".", 3)[-1] if c.startswith("ncf.") else c
                for c in first["not_covered"]
            }
        ]
    lines = [
        [x] for x in read_me(t, step, len(objectives), len(rubric), len(uncovered)) if x
    ]
    if first:
        lines.insert(1, [first["why"]])
    body, ids = (
        [HEADER],
        {r["row"]: r["claims"] for r in rows(t, step)[0] + rows(t, step)[2]},
    )
    for r in objectives:
        code, unit, title, say, ncf, cam, ncert, builds, tested, repeats, optional = r[
            "cells"
        ]
        notes = "; ".join(
            x
            for x in (
                f"Unit: {unit}",
                f"Repeats in: {repeats}" if repeats != "—" else "",
                f"Optional: {optional}" if optional else "",
            )
            if x
        )
        body.append(
            [
                r["row"],
                "Objective",
                code,
                title,
                say,
                ncf,
                cam,
                ncert,
                builds,
                tested,
                notes,
                "",
                "",
            ]
        )
        ids[r["row"]] = r["claims"]
    for r in rubric:
        part, text, notes = r["cells"]
        body.append(
            [
                r["row"],
                "Outcome" if r["row"] == "R1" else "Rubric line",
                step,
                part,
                text,
                "",
                "",
                "",
                "",
                "",
                notes,
                "",
                "",
            ]
        )
        ids[r["row"]] = r["claims"]
    for r in uncovered:
        where, text, detail, why = r["cells"]
        ncf, cam = (text, "") if "NCF-SE" in where else ("", text)
        body.append(
            [
                r["row"],
                "Not covered yet",
                where,
                "",
                detail,
                ncf,
                cam,
                "",
                "",
                "",
                why,
                "",
                "",
            ]
        )
        ids[r["row"]] = r["claims"]
    statements = {(s["framework_code"], s["code"]): s for s in t["framework_statement"]}
    cited = sorted(
        {
            a["statement_code"]
            for a in t["alignment"]
            if a["framework_code"].startswith("NCERT")
            and a["lo_code"] in {o["cells"][0] for o in objectives}
        }
    )
    notes = [["NCERT outcomes cited above, word for word:"]]
    notes += [
        [
            f"{c} ({statements[('NCERT-LO-2017', c)]['level_code']}, p{statements[('NCERT-LO-2017', c)]['pdf_page']}): "
            f"{whole(statements[('NCERT-LO-2017', c)])}"
        ]
        for c in cited
    ]
    shown = {o["cells"][0] for o in objectives}
    used = {a["framework_code"] for a in t["alignment"] if a["lo_code"] in shown}
    notes += [[], ["Sources:"]]
    for d in t["framework_document"]:
        if d["framework_code"] in used:
            f = next(f for f in t["framework"] if f["code"] == d["framework_code"])
            kind = (
                "a copy found on another site"
                if d["provenance"] == "third_party_copy"
                else "the publisher's own"
            )
            edition = re.split(r" \(|;", f["edition"])[0]
            notes.append([f"{f['name']}, {edition} — {kind}: {d['url']}"])
    return lines + [[]] + body + [[]] + notes, ids


def sheet_csv(step):
    """The one-tab table as CSV, and its rows' claims kept for reading the decisions back."""
    import csv

    grid, ids = table(step)
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{slug(step)}.csv"
    with path.open("w", newline="") as f:
        csv.writer(f).writerows(grid)
    review = CW / "review"
    review.mkdir(parents=True, exist_ok=True)
    (review / f"{slug(step)}.rows.json").write_text(json.dumps(ids, indent=1) + "\n")
    return path


SHORT = {
    "NCF-SE-2023": "NCF-SE’s",
    "NCERT-LO-2017": "NCERT’s",
    "NCERT-LO-2019": "NCERT’s",
}


def title(t, step):
    """The step in the school's words: "Mathematics · Number · ages 8 to 9 (Grade 3)"."""
    s = next(x for x in t["progression_step"] if x["code"] == step)
    p = next(x for x in t["progression"] if x["code"] == s["progression_code"])
    design = json.loads((CW / "design.json").read_text())
    subject = next(x["name"] for x in design["subjects"] if x["code"] == p["subject"])
    grade = s["age_from"] - design["grade_age"]["grade_1_from"] + 1
    school = f" (Grade {grade})" if grade >= 1 else ""
    return f"{subject} · {p['strand']} · ages {s['age_from']} to {s['age_to']}{school}"


def read_me(t, step, n_objectives, n_rubric, n_uncovered):
    s = next(x for x in t["progression_step"] if x["code"] == step)
    subject = next(
        p["subject"] for p in t["progression"] if p["code"] == s["progression_code"]
    )
    design = json.loads((CW / "design.json").read_text())
    own = next(x["cambridge"] for x in design["subjects"] if x["code"] == subject)
    at = [
        f"{SHORT.get(lv['framework_code'], 'Cambridge’s')} {lv['code']}"
        for lv in t["framework_level"]
        if lv["age_from"] <= s["age_from"] < lv["age_to"]
        and lv["framework_code"] in (own, "NCF-SE-2023", "NCERT-LO-2017")
    ]
    levels = sorted(t["rubric_level"], key=lambda lv: lv["ord"])
    return [
        f"The curriculum crosswalk: a sample for approval — {title(t, step)}",
        "",
        "What this is: for each of the school's objectives on this step, what NCF-SE, Cambridge and NCERT say at this "
        "age, and what we say, drafted by one method with one way of thinking. Then the step's outcome and a rubric "
        "line for each level, and the official statements no objective covers yet.",
        "",
        "What we ask of you: nothing to write. On each row, put one word in the Decision column: Approve, Change or "
        "Reject. Add a comment only if you want the draft changed or you reject it; the method redrafts from your "
        "comment.",
        f"Rows to decide: {n_objectives} objectives, {n_rubric} outcome and rubric rows, {n_uncovered} statements not "
        "covered.",
        "",
        f"Age is the anchor. This step is ages {s['age_from']} to {s['age_to']}, the age of Grade 3 by NCF-SE (page 62). "
        f"At this age: {', '.join(at)}. Cambridge prints 'typically for learners aged 5 to 11' for its six stages, so "
        "a stage's age is worked out, one year each. The school's Grade 3 objectives already mix Cambridge Stage 3 and "
        "Stage 4. Codes such as 3Np.01 are Cambridge's (Stage 3, Number, place value, objective 1); C-1.1 is NCF-SE's.",
        "",
        "The relation words: meets (asks for the same, at this age); goes further than (asks for more); partly meets "
        "(covers part; the reason names what is left); prepares for (the statement sits a year later).",
        "",
        "The rubric levels: "
        + "; ".join(
            f"{lv['label']}: {lv['meaning']} (the national card's {lv['reports_as']})"
            for lv in levels
        )
        + ".",
        "",
        "The Cambridge texts come from copies of Cambridge's publications found on other schools' sites, recorded with "
        "their address and fingerprint (listed at the end). When the school's official copies arrive, they are "
        "compared statement by statement.",
        "",
        "Only a decision by the signatory makes a row the school's word. A row nobody decides stays a proposal.",
    ]


def main(argv):
    if len(argv) != 1:
        print(__doc__.strip().splitlines()[-1])
        return 2
    print(f"the sheet for {argv[0]}: {sheet_csv(argv[0]).relative_to(R)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
