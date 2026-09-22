"""ADR 0032's proof: a child's signed-off paper read again twice — as the reader was before the
notebook existed, and with the notebook built from the child's OTHER papers — both scored against what
people confirmed. A check must change a later read, or the loop is not built
(`correction_must_change_a_later_read`).
"""

import json
from pathlib import Path

from engine import legacy, profiles, reading, reread
from engine.adapters import ocr


def score(readings, truth):
    """The answers people settled on this page, as the reader now reads them: right and stood behind;
    wrong and stood behind (the silent error rule 5 exists to stop); or flagged for a person — with
    the right guess (one click) or without (typing)."""
    out = {"n": 0, "right": 0, "silently_wrong": 0, "flagged": 0, "one_click": 0, "typing": 0, "missing": 0}
    for key, want in truth.items():
        r = readings.get(key)
        if r is None:
            out["missing"] += 1
            continue
        out["n"] += 1
        want = profiles._norm(want)
        if profiles.doubted(r.get("why") or "") or r.get("answer_state") not in ("written", "blank"):
            out["flagged"] += 1
            guess = profiles._norm(r.get("guess") or "")
            out["one_click" if guess and guess == want else "typing"] += 1
        elif profiles._norm(r.get("child_answer") or "") == want:
            out["right"] += 1
        else:
            out["silently_wrong"] += 1
    return out


def run(conn, child_ids, cli=None, second=True):
    """→ one dict per signed-off paper of each child: the scores without and with the notebook."""
    cli = cli or ocr.client()
    by_child = {}
    for r in profiles.checked_rows(conn):
        by_child.setdefault(str(r["child_id"]), []).append(r)
    files = {(str(f["child_id"]), str(Path(f["path"]).expanduser())): f for f in reread.files(conn)}
    report = []
    for child in child_ids:
        mine = by_child.get(str(child), [])
        for capture_id in dict.fromkeys(str(r["capture_id"]) for r in mine):
            on_paper = [r for r in mine if str(r["capture_id"]) == capture_id]
            first = on_paper[0]
            path = Path(first["path"]).expanduser()
            f = files.get((str(child), str(path)))
            result = {"child": str(child), "paper": first["paper"], "file": path.name, "n": len(on_paper)}
            if not f or not path.exists():
                report.append({**result, "skipped": "scan not on this machine"})
                continue
            template, by_key = legacy.paper_rows(conn, first["paper"])
            paper = template["key"] if isinstance(template["key"], dict) else json.loads(template["key"])
            pages = sorted(f["pages"])
            scan = {
                "path": str(path),
                "paper_code": first["paper"],
                "paper": paper,
                "by_key": by_key,
                "page_numbers": pages,
                "images": legacy.render_pages(str(path), pages),
                "masks": None,
            }
            truth = {r["item_key"].rsplit("/", 1)[1]: r["human_read"] for r in on_paper}
            others = [r for r in mine if str(r["capture_id"]) != capture_id]
            notebook = profiles.build(others)
            for label, notes, sec in (("without", {}, False), ("with", notebook, second)):
                readings = {}
                for pg in reading.read_pages(conn, scan, cli, child, notes=notes, second=sec):
                    readings.update(pg["readings"] or {})
                result[label] = score(readings, truth)
            result["notebook"] = {
                "checks": len(others),
                "floor": notebook["floor"],
                "route": notebook["route"],
                "confusions": notebook["confusions"],
                "samples": len(notebook["samples"]),
            }
            report.append(result)
    return report


def totals(report, label):
    keys = ("n", "right", "silently_wrong", "flagged", "one_click", "typing", "missing")
    return {k: sum(r[label][k] for r in report if label in r) for k in keys}
