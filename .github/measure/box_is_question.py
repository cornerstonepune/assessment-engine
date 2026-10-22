"""Whether the picture shown for an answer waiting for a person is that answer's own question (goals/ck1), read only.
Run inside the engine by engine-logs.yml. Counts by kind of paper and by cause: never a child's name, an answer or a scan
(rule 6).

For every answer a person still has to check: (c) no box; (b) a box another question of the same page also has; (a) a box
that, laid over the printed paper's own layout (`<pdf>.key.json`'s boxes, in mm), sits nearer another question's boxes than
its own. The layout is mapped to the page as shown by a straight line per axis fitted through the page's own boxes,
twice, the second time without the ones that sat far from the first line, so a few wrong boxes do not move it."""

import json
from collections import Counter
from pathlib import Path

import numpy as np

from engine.core import db
from engine.w3_read import printed_paper

A4 = (210.0, 297.0)
FAR = 0.08  # of a page: a box this far from the fitted line is left out of the second fit


def _fit(pairs):
    """pairs [(printed, shown)] on one axis → (scale, offset), fitted twice, the second without the far ones."""
    p, s = np.array(pairs, float).T
    keep = np.ones(len(p), bool)
    for _ in range(2):
        if keep.sum() < 2 or np.ptp(p[keep]) < 1e-6:
            return None
        a, b = np.polyfit(p[keep], s[keep], 1)
        keep = np.abs(a * p + b - s) < FAR
    return a, b


def _centre(box):
    return (box[0] + box[2]) / 2, (box[1] + box[3]) / 2


def page_verdicts(answers, cells):
    """answers: [(key, item, rid, box|None)] of one page of one copy; cells: that page's printed boxes {(item, rid): (x, y)}
    in mm. → {key: (kind, cause)}, kind in own / other / none / shared."""
    out = {}
    boxed = [a for a in answers if a[3]]
    for key, item, rid, box in answers:
        if not box:
            out[key] = ("none", "no box stored")
    seen = Counter(tuple(a[3]) for a in boxed)
    for key, item, rid, box in boxed:
        sharers = {a[1] for a in boxed if tuple(a[3]) == tuple(box)}
        if len(sharers) > 1:
            out[key] = ("shared", f"one box for {len(sharers)} questions" if seen[tuple(box)] else "")
    pairs = [(cells[(i, r)], _centre(b)) for _, i, r, b in boxed if (i, r) in cells]
    if len(pairs) < 3:
        for key, *_ in boxed:
            out.setdefault(key, ("unchecked", "fewer than 3 boxes on the page to lay over the layout"))
        return out
    fx, fy = _fit([(p[0] / A4[0], s[0]) for p, s in pairs]), _fit([(p[1] / A4[1], s[1]) for p, s in pairs])
    if fy is None:  # the question's place down the page is what tells one from another; across it may not vary
        for key, *_ in boxed:
            out.setdefault(key, ("unchecked", "the boxes cannot be laid over the layout"))
        return out
    items = {i for i, _ in cells}
    fx = fx or (0.0, 0.0)  # no spread across: nothing to tell by, so every box counts as at 0 on that axis
    where = {i: [(x / A4[0] * fx[0] + fx[1], y / A4[1] * fy[0] + fy[1]) for (j, _), (x, y) in cells.items() if j == i]
             for i in items}
    for key, item, rid, box in boxed:
        if key in out:
            continue
        cx, cy = _centre(box)
        cx = cx if any(fx) else 0.0
        near = min(items, key=lambda i: min((cx - x) ** 2 + (cy - y) ** 2 for x, y in where.get(i, [(9, 9)])))
        out[key] = ("own", "") if near == item else ("other", f"nearest the layout of {near}")
    return out


def main():
    sql = (
        "select r.id, c.id as capture, si.kind, c.path, si.pdf_path, t.source, t.id as template_id,"
        " coalesce(t.code, t.batch_id) as code, i.item_key, r.rid, r.raw_read::jsonb as raw"
        " from item_result r join capture c on c.id = r.capture_id join item i on i.id = r.item_id"
        " join sheet_instance si on si.id = c.sheet_instance_id join sheet_template t on t.id = si.sheet_template_id"
        " where c.superseded_by is null and r.state = 'candidate' and r.status in ('unreadable', 'needs_teacher')"
        " order by c.id, r.id"
    )
    total, causes, pages = Counter(), Counter(), {}
    with db.connect() as conn:
        conn.execute("set transaction read only")
        for r in conn.execute(sql).fetchall():
            raw = r["raw"] or {}
            pages.setdefault((r["capture"], raw.get("file_page") or raw.get("page") or 1), []).append(r)
        for (capture, file_page), rows in pages.items():
            first = rows[0]
            kind = first["kind"] or "?"
            geometry = []
            mine = {"pdf_path": first["pdf_path"], "source": first["source"], "template_id": first["template_id"]}
            try:
                pdf = printed_paper.read_from(conn, first["code"], mine, Path(first["path"]).expanduser())
                geometry = printed_paper._named_now(conn, printed_paper.boxes_drawn(pdf)) if pdf else []
            except Exception as e:  # noqa: BLE001 a measure says what failed and goes on
                causes[(kind, "layout not read: " + type(e).__name__)] += 1
            page_of = {c["item"]: c["page"] for c in geometry}
            on = page_of.get(first["item_key"])
            cells = {}
            for g in geometry:
                if g.get("kind") == "digit" and g["page"] == (rows[0]["raw"] or {}).get("page", on):
                    cells.setdefault((g["item"], g["resp"]), []).append((g["x"] + g["w"] / 2, g["y"] + g["h"] / 2))
            cells = {k: tuple(np.mean(v, axis=0)) for k, v in cells.items()}
            answers = [(str(r["id"]), r["item_key"], r["rid"], (r["raw"] or {}).get("box")) for r in rows]
            verdict = page_verdicts(answers, cells)
            for r in rows:
                raw = r["raw"] or {}
                kind_of, why = verdict.get(str(r["id"]), ("unchecked", "no layout kept"))
                total[(kind, kind_of)] += 1
                extra = []
                if page_of.get(r["item_key"]) not in (None, raw.get("page")):
                    extra.append("stored page differs from the layout's page for the question")
                if raw.get("file_page") not in (None, raw.get("page")):
                    extra.append("copy's file page differs from the paper's page")
                if kind_of in ("other", "shared", "none") or extra:
                    causes[(kind, kind_of, why, "; ".join(extra))] += 1
    print("-- by kind of paper: answers waiting for a person, by what the picture shows")
    for (kind, k), n in sorted(total.items()):
        print(f"  {kind} | {k} | {n}")
    print("-- causes")
    for key, n in sorted(causes.items(), key=lambda t: -t[1]):
        print("  " + " | ".join(str(p) for p in key) + f" | {n}")
    print("-- pages", len(pages), "answers", sum(total.values()), json.dumps({"fit_far": FAR}))


if __name__ == "__main__":
    main()
