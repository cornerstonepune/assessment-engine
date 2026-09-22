"""ADR 0032 — a second reader for what the first gave up on.

The vision model is shown this child's own confirmed handwriting (the notebook's samples, re-cut from
the scans on this machine) and the crop the first reader could not settle, and says what it reads
there. It never settles an answer — ADR 0019's reason stands, a model that knows arithmetic must not be
the one that settles a digit — it proposes: the one-click guess a person confirms. It is not shown the
question, for the same reason. It ships with its eval (`engine read guess --eval`, rule 7).
"""

from pathlib import Path

from engine import legacy, profiles
from engine.adapters import llm

PURPOSE = "read_with_examples"


def crop_of(path, file_page, box, cfg):
    """One answer's patch of the page, drawn at the second-look size (`ocr.reread_dpi`)."""
    p = str(Path(path).expanduser())
    jpeg = legacy._sharp_page(p, Path(p).stat().st_mtime, file_page, int(cfg.get("reread_dpi") or 300))
    return legacy.crop(jpeg, list(box), pad=cfg.get("reread_pad", 0.012))


def examples(conn, notes, cfg, exclude_capture=None):
    """[(crop, what the child wrote)] for the notebook's samples that are on this machine — never one
    from `exclude_capture`, so a replay does not show the reader the very page it is being tested on."""
    out = []
    for s in notes.get("samples") or []:
        if exclude_capture and str(s["capture_id"]) == str(exclude_capture):
            continue
        cap = conn.execute("select path, pages from capture where id = %s", (s["capture_id"],)).fetchone()
        if not cap or not Path(cap["path"]).expanduser().exists():
            continue
        out.append((crop_of(cap["path"], s["page"] if cap["pages"] > 1 else 1, s["box"], cfg), s["text"]))
    return out


def ask(conn, target, n_answers, samples):
    """→ the second reader's answers for one crop, in order; "" where it read nothing."""
    labelled = "\n".join(f"Image {i}: the child wrote {text!r}" for i, (_, text) in enumerate(samples, 1))
    out = llm.generate(
        conn,
        PURPOSE,
        {"k": len(samples), "examples": labelled or "(none yet)", "n": n_answers},
        images=[jpeg for jpeg, _ in samples] + [target],
    )
    answers = [str(a).strip() for a in out["answers"]][:n_answers]
    return answers + [""] * (n_answers - len(answers))


def _groups(readings):
    """The doubted readings of a page, grouped by the region they share (one question's answers),
    each member in slot order. A question whose answer is not a number is a person's to type."""
    groups = {}
    for slot, r in readings.items():
        why = r.get("why") or ""
        if not profiles.doubted(why) or r.get("guess") or not r.get("box") or "not a number" in why:
            continue
        groups.setdefault(tuple(r["box"]), []).append(slot)
    return {box: sorted(members) for box, members in groups.items()}


def propose(conn, readings, path, file_page, notes, cfg, exclude_capture=None):
    """The page's doubted readings, each given the second reader's guess. One call per question; a
    call that fails leaves that question's readings as they were and says so in the note."""
    groups = _groups(readings)
    if not groups:
        return readings, ""
    samples = examples(conn, notes, cfg, exclude_capture)
    out, failed = dict(readings), 0
    for box, members in groups.items():
        try:
            answers = ask(conn, crop_of(path, file_page, box, cfg), len(members), samples)
        except llm.LLMError:
            failed += 1
            continue
        for slot, answer in zip(members, answers):
            out[slot] = {
                **out[slot],
                "guess": answer,
                "guess_by": f"{PURPOSE} with {len(samples)} of the child's answers",
            }
    note = f"second reader: {len(groups) - failed} of {len(groups)} questions given a guess, {len(samples)} samples shown"
    return out, note


# ---------------------------------------------------------------- the answers already waiting, and the eval


def _waiting(conn, child_ids=None):
    return conn.execute(
        "select r.id, r.raw_read, c.id as capture_id, c.path, c.pages as file_pages, si.child_id,"
        "       coalesce((i.spec ->> 'page')::int, 1) as page, i.item_key"
        " from item_result r join item i on i.id = r.item_id join capture c on c.id = r.capture_id"
        " join sheet_instance si on si.id = c.sheet_instance_id"
        " where c.superseded_by is null and r.state = 'candidate' and r.status in ('unreadable', 'needs_teacher')"
        "   and not exists (select 1 from read_correction rc where rc.item_result_id = r.id)"
        "   and (%s::uuid[] is null or si.child_id = any(%s::uuid[]))"
        " order by c.id, page, i.item_key",
        (child_ids, child_ids),
    ).fetchall()


def backfill(conn, cfg, child_ids=None):
    """Every answer waiting for a person that the reader gave up on, given a guess now — so the queue
    people are working today turns from typing into clicking. Returns (guessed, questions asked)."""
    import json

    by_page = {}
    for r in _waiting(conn, child_ids):
        read = json.loads(r["raw_read"]) if isinstance(r["raw_read"], str) else (r["raw_read"] or {})
        by_page.setdefault((str(r["capture_id"]), r["page"]), []).append((r, read))
    guessed = asked = 0
    for (capture_id, page), rows in by_page.items():
        readings = {r["item_key"].rsplit("/", 1)[1]: read for r, read in rows}
        if not _groups(readings):
            continue
        first = rows[0][0]
        if not Path(first["path"]).expanduser().exists():
            continue
        notes = profiles.for_child(conn, first["child_id"])
        got, _ = propose(conn, readings, first["path"], page if first["file_pages"] > 1 else 1, notes, cfg)
        asked += len(_groups(readings))
        for r, read in rows:
            new = got[r["item_key"].rsplit("/", 1)[1]]
            if new.get("guess") and new != read:
                conn.execute("update item_result set raw_read = %s where id = %s", (json.dumps(new), r["id"]))
                guessed += 1
    return guessed, asked


def evaluate(conn, cfg, child_ids=None):
    """The eval (rule 7): every answer a person has settled that the first reader gave up on, guessed
    again by the second reader shown that child's notebook built WITHOUT the paper under test, and
    scored against what the person said. Returns the tally and the model spend."""
    rows = [
        r
        for r in profiles.checked_rows(conn)
        if profiles.doubted(r["why"])
        and r["box"]
        and "not a number" not in r["why"]
        and (not child_ids or str(r["child_id"]) in {str(c) for c in child_ids})
        and Path(r["path"]).expanduser().exists()
    ]
    by_child = {}
    for r in profiles.checked_rows(conn):
        by_child.setdefault(str(r["child_id"]), []).append(r)
    from engine import external  # external imports legacy, which imports this module: lazily, at call time

    spent = external.spend_today(conn)
    tally = {"n": 0, "right": 0, "by_kind": {}, "details": []}
    by_page = {}
    for r in rows:
        by_page.setdefault((str(r["capture_id"]), r["page"]), []).append(r)
    for (capture_id, page), group in by_page.items():
        child = str(group[0]["child_id"])
        notes = profiles.build([x for x in by_child[child] if str(x["capture_id"]) != capture_id])
        readings = {
            r["item_key"].rsplit("/", 1)[1]: {"why": r["why"], "box": r["box"], "guess": ""} for r in group
        }
        got, _ = propose(
            conn,
            readings,
            group[0]["path"],
            page if group[0]["file_pages"] > 1 else 1,
            notes,
            cfg,
            exclude_capture=capture_id,
        )
        for r in group:
            guess = got[r["item_key"].rsplit("/", 1)[1]].get("guess", "")
            right = profiles._norm(guess) == profiles._norm(r["human_read"])
            k = tally["by_kind"].setdefault(r["fmt"], {"n": 0, "right": 0})
            k["n"] += 1
            k["right"] += right
            tally["n"] += 1
            tally["right"] += right
            tally["details"].append(
                (r["paper"], r["item_key"].rsplit("/", 1)[1], r["human_read"], guess, right)
            )
    tally["spend_inr"] = external.spend_today(conn) - spent
    return tally
