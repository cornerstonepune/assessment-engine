"""What the engine read on the newest scan, answer by answer, to grade it against a person's reading by page (read
only). Pages, codes, questions and reads only: never a child's name or an image (rule 6). Each answer carries its
question number on the sheet (`raw_read.slot`) and the paper's page; each copy, the reader's note for each page and
how much of each printed page the box reader found on the photograph (`lineup`), so a page read by its words instead
of its boxes says why."""

import json
from pathlib import Path

import numpy as np

from engine.core import db
from engine.w3_read import lineup, render_pdf


def _lines_up(scan, pdf, page):
    """(tiles found, tiles the printed page has, the share `lineup.line_up` needs) for one photographed page."""
    img, _ = render_pdf.photo(scan, page)
    printed = lineup._printed(str(pdf), page)
    small, s = lineup._grey(img, lineup.SIDE)
    maps = [m for m in (lineup._by_orb(small, s, printed), lineup._by_sift(img, printed)) if m is not None]
    found = max((len(lineup._found(small, s, m, printed)) for m in maps), default=0)
    return found, len(printed[4]), lineup.ENOUGH


with db.connect() as c:
    run = c.execute(
        "select id, trigger, status, started_at, finished_at, result from flow_run"
        " where flow = 'read-scan' order by started_at desc limit 1"
    ).fetchone()
    print("-- run", run["status"], run["started_at"], run["finished_at"], "pages", (run["result"] or {}).get("pages"))
    for cp in (run["result"] or {}).get("copies", []):
        meta = {k: cp.get(k) for k in ("copy", "pages", "code", "answers", "skipped", "why", "lacks", "no_code", "missing", "notes")}
        print("== copy", json.dumps(meta))
        if not cp.get("capture_id"):
            continue
        cap = c.execute(
            "select c.path, si.pdf_path from capture c left join sheet_instance si on si.id = c.sheet_instance_id"
            " where c.id = %s",
            (cp["capture_id"],),
        ).fetchone()
        pdf = cap and cap["pdf_path"]
        print("  printed pdf kept:", bool(pdf and Path(pdf).exists()))
        if pdf and Path(pdf).exists() and cap["path"] and Path(cap["path"]).exists():
            for p in range(1, 3):
                try:
                    print("  lineup page", p, "found / tiles / needs", _lines_up(cap["path"], pdf, p))
                except Exception as e:  # noqa: BLE001 — a measure says what failed and goes on
                    print("  lineup page", p, "failed:", type(e).__name__)
        rows = []
        for r in c.execute(
            "select r.rid, r.status, r.state, r.read_confidence, r.working_shown, r.raw_read,"
            " a.standing from item_result r left join answer_standing a on a.item_result_id = r.id"
            " where r.capture_id = %s",
            (cp["capture_id"],),
        ):
            raw = r["raw_read"] or ""
            try:
                j = json.loads(raw)
            except (ValueError, TypeError):
                j = {}
            slot = str(j.get("slot") or "?")
            keep = {k: j.get(k) for k in ("read", "value", "guess", "box", "why") if j.get(k) not in (None, "")}
            rows.append((float(slot.split(".")[0]) if slot.split(".")[0].isdigit() else 99.0, slot, j.get("page"), r, keep))
        for _, slot, page, r, keep in sorted(rows, key=lambda t: (t[0], t[1])):
            print("  Q" + slot, "p", page, r["status"], r["state"], r["standing"], r["read_confidence"], r["working_shown"],
                  json.dumps(keep, default=str))
_ = np  # the photograph arrays lineup returns are numpy's
