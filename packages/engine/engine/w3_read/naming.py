"""W3/N9 — the mistake behind a wrong answer that no named mistake explains, named by a person (ADR 0036): Jev's three
likeliest first (`w1_bank/mistake_guess`), and every named mistake of the operation for when those three miss. Kept
append-only against the reading it was named on (`mistake_named`); the answer's mark carries it, and `marking` keeps a
naming whenever the same reading is saved again (`named`). Its own module since marking an equation's boxes together
(goals/s24-a-split-that-holds-is-right.yaml) took `marking.py` past the 400-line ceiling: marking says whether an
answer is right, this says why a wrong one is wrong."""

import json

from engine.w1_bank import mistake_guess


def named(conn, result_id, answer):
    """The mistake a person last named for this answer, on this reading of it: [code], or [] (none, or not named)."""
    row = conn.execute(
        "select code from mistake_named where item_result_id = %s and answer = %s order by created_at desc limit 1",
        (result_id, answer),
    ).fetchone()
    return [row["code"]] if row and row["code"] != mistake_guess.NONE else []


def _waiting(conn, where, arg):
    """Wrong answers not yet signed off that no mistake is named for, with what the child wrote."""
    rows = conn.execute(
        "select r.id, i.spec, r.raw_read,"
        " (select rc.human_read from read_correction rc where rc.item_result_id = r.id"
        "  order by rc.created_at desc limit 1) as typed"
        " from item_result r join item i on i.id = r.item_id"
        f" where {where} and r.state = 'candidate' and r.status = 'wrong' and r.misconception_codes = '{{}}'",
        (arg,),
    ).fetchall()
    out = []
    for r in rows:
        answer = (
            r["typed"]
            if r["typed"] is not None
            else json.loads(r["raw_read"] or "{}").get("child_answer", "")
        )
        named = conn.execute(
            "select 1 from mistake_named where item_result_id = %s and answer = %s", (r["id"], answer)
        ).fetchone()
        if not named:
            out.append((r, answer))
    return out


def unnamed(conn, capture_id):
    """{result_id: {"answer", "shortlist": [[code, chance], …], "options": [every code], "why"}} for a paper's wrong
    answers that no named mistake explains and no person has named yet — Jev's three likeliest, or NONE
    (`w1_bank/mistake_guess`, ADR 0036), and every named mistake of the operation for when those three miss. Jev
    unreachable is not a failure of the page: the shortlist is empty and `why` says so."""
    out = {}
    for r, answer in _waiting(conn, "r.capture_id = %s", capture_id):
        op = (r["spec"] or {}).get("op")
        if op not in mistake_guess.SIGN:
            continue
        why = ""
        try:
            short = mistake_guess.shortlist(conn, r["spec"], answer) or []
        except mistake_guess.jev.JevError as e:
            short, why = [], f"Jev could not be asked: {e}"
        out[str(r["id"])] = {
            "answer": answer,
            "shortlist": [[c, p] for c, p in short],
            "options": list(mistake_guess.options(op)),
            "why": why,
        }
    return out


def name_mistake(conn, result_id, code, by, proposed=()):
    """A person names the mistake behind a wrong answer no named mistake explains: one of its operation's named
    mistakes, or NONE. Kept (append-only) against the reading it was named on; the answer's mark carries it."""
    found = _waiting(conn, "r.id = %s", result_id)
    if not found:
        raise ValueError(f"no wrong answer waiting to be named with id {result_id}")
    row, answer = found[0]
    op = (row["spec"] or {}).get("op")
    if op not in mistake_guess.SIGN or code not in mistake_guess.options(op):
        raise ValueError(f"{code!r} is not a named mistake of {op!r}, nor {mistake_guess.NONE}")
    conn.execute(
        "insert into mistake_named (tenant_id, item_result_id, answer, code, proposed, by, created_at)"
        " select tenant_id, id, %s, %s, %s, %s, clock_timestamp() from item_result where id = %s",
        (answer, code, json.dumps([list(x) for x in proposed]), by, result_id),
    )
    conn.execute(
        "update item_result set misconception_codes = %s, updated_at = now() where id = %s",
        ([] if code == mistake_guess.NONE else [code], result_id),
    )
    return {"code": code, "answer": answer}
