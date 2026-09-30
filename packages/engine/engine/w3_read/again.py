"""W3/N9 — every answer marked again when its rule or its key changes, with no page read again.
- `remark` covers what the reader read and no person has seen.
- `mark_again` covers what a person typed the reading of (ADR 0044).
- `by_new_key` covers, for one question whose right answer an educator changed (`keys.change`, ADR 0045), what was
  signed off as the reader read it; a person's own call and a judgement are never overwritten.
What was read never changes; only the mark does, and a signed-off answer's mark only with a new batch of evidence, the
old one kept."""

import json

from engine.w1_bank import learned as learned_mistakes
from engine.w3_read import marking, profiles


def remark(conn, child_id, item_id=None):
    """Mark every candidate again from what was read, without asking the model again — for when the marking rule
    improves after a page was read. `child_id` and `item_id` narrow it to one child, one question, or both. Returns how
    many rows changed.

    An answer a person has settled — typed what the child wrote, or judged it — is never marked again
    from the reader's own reading: that would put back the very reading the person corrected. Nor is
    a reading a later read superseded: it is history, and nothing else reads it either. A wrong or a
    blank the engine settled alone before ADR 0029 is held for a person here, its reading unchanged."""
    rows = conn.execute(
        "select r.id, r.capture_id, r.item_id, r.raw_read, r.status, r.misconception_codes, r.working_shown, i.spec,"
        " i.responses, i.fmt from item_result r join item i on i.id = r.item_id"
        " join capture c on c.id = r.capture_id join sheet_instance si on si.id = c.sheet_instance_id"
        " where (%(c)s::uuid is null or si.child_id = %(c)s) and (%(i)s::uuid is null or r.item_id = %(i)s)"
        " and r.state = 'candidate' and r.raw_read is not null and c.superseded_by is null"
        " and not exists (select 1 from read_correction rc where rc.item_result_id = r.id)",
        {"c": child_id, "i": item_id},
    ).fetchall()
    changed = 0
    trust, rate, learned = profiles.kind_trust(conn), marking.spot_rate(conn), learned_mistakes.rules(conn)
    for r in rows:
        status, codes, working, read = marking.mark_read(
            r["spec"], r["responses"][0], json.loads(r["raw_read"]), trust.get(r["fmt"], marking.UNTRUSTED),
            spot=marking.spot_checked(r["capture_id"], r["item_id"], rate),  # the same sample as when it was read
            learned=learned,
        )  # fmt: skip
        if (status, codes, working) != (r["status"], list(r["misconception_codes"]), r["working_shown"]):
            conn.execute(
                "update item_result set status = %s, misconception_codes = %s, working_shown = %s,"
                " raw_read = %s where id = %s",
                (status, codes, working, json.dumps(read), r["id"]),
            )
            changed += 1
    return changed


class _Held(Exception):
    pass


def _settle(conn, r, mark, by):
    """One answer's new mark; a signed-off one with a new batch of evidence in `by`'s name (`correct_signed_off`), the
    batch before it kept, or not at all → why it was held, or None."""
    try:
        with conn.transaction():
            conn.execute(
                "update item_result set status = %s, misconception_codes = %s, working_shown = %s,"
                " updated_at = now() where id = %s",
                (*mark, r["id"]),
            )
            evidence = "select correct_signed_off(%s, %s) as n"
            if r["state"] == "confirmed" and not conn.execute(evidence, (r["id"], by)).fetchone()["n"]:
                raise _Held
    except _Held:
        return f"{mark[0]} makes no evidence"
    return None


def mark_again(conn, by, item_id=None):
    """Every answer a person typed the reading of, marked again by the rule and key as they now stand, as `correct`
    marks it → (changed, left): (its question's key, the mark it had, the mark it has) for each answer whose mark
    changed, and (its question's key, the mark it keeps, why) for each a signed-off answer cannot take.
    - One not yet signed off changes in place; one signed off gets a new batch of evidence in `by`'s name.
    - What a person read stays. A person's judgement is theirs, and is never marked again.
    `item_id` limits it to one question (`keys.change`).
    2026-09-30: "false" for "odd + odd = odd" stayed wrong on every paper signed off before the rule was put right."""
    rows = conn.execute(
        "select r.id, r.capture_id, r.state, r.status, r.raw_read, i.item_key, i.spec, i.responses,"
        " k.human_read as typed, k.judged from item_result r join item i on i.id = r.item_id"
        " join capture c on c.id = r.capture_id"
        " join lateral (select human_read, judged from read_correction where item_result_id = r.id"
        " order by created_at desc limit 1) k on true"
        " where r.state in ('candidate', 'confirmed') and c.superseded_by is null and k.judged is null"
        " and k.human_read is not null"
        " and (%(i)s::uuid is null or r.item_id = %(i)s)",
        {"i": item_id},
    ).fetchall()
    learned, changed, left = learned_mistakes.rules(conn), [], []
    for r in rows:
        holds = (r["spec"] or {}).get("holds")
        right = marking._group(conn, r["capture_id"], holds, {})[r["id"]][2] if holds else False
        mark = marking._as_read(conn, r, r["typed"], right, learned)
        if mark[0] != r["status"]:
            held = _settle(conn, r, mark, by)
            (left if held else changed).append((r["item_key"], r["status"], held or mark[0]))
    return changed, left


def by_new_key(conn, by, item_id, was):
    """A question's right answer changed from `was` (`keys.change`, ADR 0045): what no person typed and a person signed
    off or judged → (changed, left), as `mark_again` returns them. Only a mark its reading gives by `was` came from that
    key; any other is a person's own call, which no key decided, and it stays.
    - Signed off as the reader read it: marked by the new right answer, with a new batch of evidence.
    - Judged by a person as `was` marked it: a judgement is never changed by the engine (ADR 0044), so it stays, and is
      named for the educator where the new right answer marks its reading otherwise.
    What a person typed is `mark_again`'s; what no person has seen yet is `remark`'s."""
    rows = conn.execute(
        "select r.id, r.state, r.status, r.raw_read, i.item_key, i.spec, i.responses, k.judged from item_result r"
        " join item i on i.id = r.item_id join capture c on c.id = r.capture_id"
        " left join lateral (select id, judged from read_correction where item_result_id = r.id"
        " order by created_at desc limit 1) k on true"
        " where r.item_id = %s and c.superseded_by is null and r.state in ('candidate', 'confirmed')"
        " and (k.judged is not null or (k.id is null and r.state = 'confirmed'))",
        (item_id,),
    ).fetchall()
    learned, changed, left = learned_mistakes.rules(conn), [], []
    for r in rows:
        reading, response = marking._read(r), r["responses"][0]
        mark = marking.mark(r["spec"], response, reading, learned)
        before = marking.mark(r["spec"], {**response, "answer": was}, reading, learned)[0]
        if mark[0] == r["status"] or before != r["status"]:
            continue
        if r["judged"] is None:
            held = _settle(conn, r, mark, by)
            (left if held else changed).append((r["item_key"], r["status"], held or mark[0]))
        else:
            said = reading.get("child_answer") or "blank"
            why = f"a person judged it by the old right answer; the new one marks its reading, {said}, {mark[0]}"
            left.append((r["item_key"], r["status"], why))
    return changed, left
