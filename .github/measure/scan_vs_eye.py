"""What the engine read on the newest scan, answer by answer, to grade it against a person's reading by page (read
only). Pages, codes, questions and reads only: never a child's name or an image (rule 6)."""

import json

from engine.core import db

with db.connect() as c:
    run = c.execute(
        "select id, trigger, status, started_at, finished_at, result from flow_run"
        " where flow = 'read-scan' order by started_at desc limit 1"
    ).fetchone()
    print("-- run", run["status"], run["started_at"], run["finished_at"], "pages", (run["result"] or {}).get("pages"))
    for cp in (run["result"] or {}).get("copies", []):
        meta = {k: cp.get(k) for k in ("copy", "pages", "code", "answers", "skipped", "why", "lacks", "no_code", "missing")}
        print("== copy", json.dumps(meta))
        if not cp.get("capture_id"):
            continue
        for r in c.execute(
            "select r.rid, r.status, r.state, r.read_confidence, r.working_shown, r.misconception_codes, r.raw_read,"
            " a.standing from item_result r left join answer_standing a on a.item_result_id = r.id"
            " where r.capture_id = %s order by r.rid",
            (cp["capture_id"],),
        ):
            raw = r["raw_read"] or ""
            try:
                j = json.loads(raw)
                raw = {k: j.get(k) for k in ("read", "value", "guess", "box", "why") if j.get(k) not in (None, "")}
            except (ValueError, TypeError, AttributeError):
                raw = raw[:160]
            print(" ", r["rid"], r["status"], r["state"], r["standing"], r["read_confidence"], r["working_shown"],
                  r["misconception_codes"], json.dumps(raw, default=str))
