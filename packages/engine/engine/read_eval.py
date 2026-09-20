"""Does a version of `legacy_extract` read a page the way a person did? `engine read eval`.

Written after v3 shipped without one and regressed the reader from 24/24 to 17/24 — by quietly
supplying the *correct* answer in seven places instead of the wrong one the child actually wrote.
Every mark came back "correct", the paper looked perfect, and nothing in the system could tell.
Rule 7 says every model output ships with an eval; this is the one that was owed.

The gold is `supabase/seed/read_gold.json`: what a person saw, by eye, on a real page. It contains
answers that are WRONG on purpose, because a reader that computes rather than transcribes scores
perfectly against a gold set of right answers and catastrophically against this one.

The number is per response, which is W3's unit (goals/w3-read-and-graph.yaml), and it is the worst
of `runs` repeats rather than one run's luck — the same guard the skill matcher needed when it
swung 84-97% across passes.
"""

import json
from pathlib import Path

from engine import db, legacy
from engine.adapters import ocr

GOLD = db.REPO_ROOT / "supabase" / "seed" / "read_gold.json"
ASSESSMENTS = "~/cornerstone/assessments"


def gold_sheets(conn=None):
    """Every hand-verified response there is: the seed file, plus every correction a teacher has
    made on the screen.

    This is the whole argument for building the approval screen early. A correction IS a
    hand-verified response — a person looked at the page and said what the child wrote — so the set
    the reader is measured against grows by using the system rather than by a data-entry project.
    The bar needs 300 responses and 100 of them phone photos (`goals/w3-read-and-graph.yaml`); 63
    were typed in by hand, and the rest should arrive as a by-product of marking.

    Where both sources hold the same answer, the teacher's is the one kept: they looked at the page
    more recently, and the seed was one person reading a screen at midnight.
    """
    sheets = json.loads(GOLD.read_text())["sheets"]
    if conn is None:
        return sheets
    # The seed names a file relative to the assessments folder and a capture names it with a ~;
    # both are the same scan, so they are matched as the one path they resolve to.
    by_file = {_resolved(sheet_name(s)): s for s in sheets}
    for row in legacy.corrections(conn):
        key = row["item_key"].rsplit("/", 1)[1]
        sheet = by_file.get(_resolved(row["path"]))
        if sheet is None:
            sheet = {
                "paper": row["paper"],
                "file": row["path"],
                "note": "from the approval screen",
                "answers": [],
            }
            by_file[_resolved(row["path"])] = sheet
            sheets.append(sheet)
        answer = {
            "n": key,
            "part": "",
            "child_answer": row["human_read"],
            "answer_state": "written" if row["human_read"] else "blank",
        }
        sheet["answers"] = [a for a in sheet["answers"] if _key(a) != key] + [answer]
    return sheets


def _resolved(file, root=None):
    return str((Path(root or ASSESSMENTS).expanduser() / Path(file).expanduser()).resolve())


def sheet_name(sheet):
    return sheet.get("file") or sheet["files"][0]


def sheet_pages(sheet, root):
    """Every page of one sitting, in order, as JPEG bytes.

    A Grade 2 sitting arrives as one scanned PDF. A Grade 3 sitting is a set of phone photographs —
    one file per page, taken on a teacher's phone — so a sheet may name `files` instead of `file`,
    and each of those is one page of the same paper.
    """
    root = Path(root).expanduser()
    files = sheet.get("files") or [sheet["file"]]
    if len(files) == 1:
        return legacy.render_pages(root / files[0])
    return [legacy.render_pages(root / f)[0] for f in files]


def _key(a):
    return f"{a['n']}{a.get('part', '')}"


def read_once_ocr(conn, sheet, root=ASSESSMENTS, cli=None):
    """One pass of the OCR reader over a gold sheet → {slot: reading} (ADR 0019)."""
    cli = cli or ocr.client()
    cfg = ocr.settings(conn)
    template, by_key = legacy.paper_rows(conn, sheet["paper"])
    paper = template["key"] if isinstance(template["key"], dict) else json.loads(template["key"])
    masks = {p["n"]: p.get("mask", 0) for p in paper["pages"]}
    out = {}
    for page_no, jpeg in enumerate(sheet_pages(sheet, root), 1):
        slots = {
            k: it["spec"]["question"] for k, it in by_key.items() if it["spec"].get("page", 1) == page_no
        }
        if not slots:
            continue  # a blank back page, or a scan longer than the paper: nothing to look for
        img = legacy.masked_image(jpeg, masks.get(page_no, 0))
        jpeg = legacy._jpeg(img)
        boxes = ocr.printed_boxes(jpeg, cfg) if paper.get("fields") == "boxes" else ()
        boxes = ocr.printed_boxes(jpeg, cfg) if paper.get("fields") == "boxes" else ()
        out.update(ocr.answers_for(ocr.read(jpeg, cli), slots, cfg, legacy.symbolic_slots(by_key), boxes))
    return out


def read_once(conn, sheet, root=ASSESSMENTS):
    """One pass of the active `legacy_extract` over a gold sheet → {key: read}.

    Reads exactly as `legacy.import_scan` does — same masks from the paper row, same expected count
    per page — so the eval measures the reader in service, not a convenient version of it.
    """
    template, by_key = legacy.paper_rows(conn, sheet["paper"])
    paper = template["key"] if isinstance(template["key"], dict) else json.loads(template["key"])
    masks = {p["n"]: p.get("mask", 0) for p in paper["pages"]}
    out = {}
    for page_no, jpeg in enumerate(sheet_pages(sheet, root), 1):
        slots = legacy.slot_list(by_key, page_no)
        img = legacy.masked_image(jpeg, masks[page_no])
        readings, _ = legacy.read_page_in_bands(conn, img, slots)
        out.update(readings)
    return out


def score(gold_answers, read):
    """→ per-response counts. `missing` is the one that hides: a response with no row at all cannot
    be corrected by anyone, because nobody is shown it."""
    exact = wrong_value = missing = state_wrong = silent = 0
    details = []
    for a in gold_answers:
        k = _key(a)
        got = read.get(k)
        if got is None:
            missing += 1
            details.append((k, a["child_answer"], "— no row —", "missing"))
            continue
        said = legacy.normalise_answer(got.get("child_answer", "") or "")
        want = legacy.normalise_answer(a["child_answer"] or "")
        if said == want:
            exact += 1
        else:
            wrong_value += 1
            # The distinction the whole bar rests on: a reading the engine STANDS BEHIND and got
            # wrong corrupts a child's graph invisibly. One it flagged costs a teacher a glance.
            #
            # `blank` is stood behind exactly as `written` is. It is not "I could not read this" —
            # it is the engine asserting the child did not answer, and it lands in the graph as a
            # skill not attempted. The Grade 3 baseline is where that showed: its comparison item
            # is answered with "<", the transcriber reads numbers only, and the region came back
            # blank at full confidence on a question the child got right. Counting only `written`
            # scored that as a quiet miss rather than the false claim it is.
            if got.get("answer_state") in ("written", "blank"):
                silent += 1
            details.append((k, want or "(blank)", said or "(blank)", got.get("answer_state", "?")))
        if "answer_state" in got and got["answer_state"] != a["answer_state"]:
            state_wrong += 1
    total = len(gold_answers)
    return {
        "total": total,
        "exact": exact,
        "wrong_value": wrong_value,
        "missing": missing,
        "state_wrong": state_wrong,
        "silently_wrong": silent,
        "silently_wrong_rate": round(silent / total, 4) if total else 0.0,
        "read_exactly_right": round(exact / total, 4) if total else 0.0,
        "responses_given_a_row": round((total - missing) / total, 4) if total else 0.0,
        "details": details,
    }


def run(conn, runs=1, root=ASSESSMENTS, reader="ocr"):
    """Every gold sheet, `runs` times. The reported rate is the WORST run, never the mean.

    `reader` picks what does the transcribing, so the two are scored by one command on one page and
    the choice is evidence rather than a vendor's benchmark.
    """
    read = read_once_ocr if reader == "ocr" else read_once
    per_run = []
    for _ in range(runs):
        agg = {
            "total": 0,
            "exact": 0,
            "wrong_value": 0,
            "missing": 0,
            "state_wrong": 0,
            "silently_wrong": 0,
            "details": [],
            "sheets": [],
        }
        for sheet in gold_sheets(conn):
            s = score(sheet["answers"], read(conn, sheet, root))
            for k in ("total", "exact", "wrong_value", "missing", "state_wrong", "silently_wrong"):
                agg[k] += s[k]
            agg["details"] += [(sheet_name(sheet), *d) for d in s["details"]]
            agg["sheets"].append({"paper": sheet["paper"], "note": sheet.get("note", ""), **s})
        agg["read_exactly_right"] = round(agg["exact"] / agg["total"], 4) if agg["total"] else 0.0
        agg["silently_wrong_rate"] = round(agg["silently_wrong"] / agg["total"], 4) if agg["total"] else 0.0
        agg["responses_given_a_row"] = (
            round((agg["total"] - agg["missing"]) / agg["total"], 4) if agg["total"] else 0.0
        )
        per_run.append(agg)
    worst = min(per_run, key=lambda r: r["read_exactly_right"])
    return worst, per_run
