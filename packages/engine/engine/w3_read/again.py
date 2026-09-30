"""W3/N9 — every answer marked again when its rule or its key changes, with no page read again.
- `remark` covers what the reader read and no person has seen.
- `mark_again` covers what a person read or signed off (ADR 0044).
Both can be limited to one question whose right answer an educator changed (`keys.change`, ADR 0045). What was read
never changes; only the mark does, and a signed-off answer's mark only with a new batch of evidence, the old one kept."""

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


def mark_again(conn, by, item_id=None):
    """Every answer a person read or signed off, marked again by the rule and key as they now stand, as `correct`
    marks it. Returns [(its question's key, the mark it had, the mark it has)] for each answer whose mark changed.
    - One not yet signed off changes in place.
    - One signed off gets a new batch of evidence in `by`'s name (`correct_signed_off`); the batch before it is kept.
    - What a person read stays. An answer signed off unchanged is marked by the reading its sign-off accepted.
    - An answer whose latest word from a person is a judgement keeps it.
    `item_id` limits it to one question (`keys.change`).
    2026-09-30: "false" for "odd + odd = odd" stayed wrong on every paper signed off before the rule was put right."""
    rows = conn.execute(
        "select r.id, r.capture_id, r.state, r.status, r.raw_read, i.item_key, i.spec, i.responses, k.judged,"
        " coalesce(k.human_read, case when r.state = 'confirmed' and r.raw_read is not null then"
        " coalesce(r.raw_read::jsonb ->> 'child_answer', '') end) as typed"
        " from item_result r join item i on i.id = r.item_id join capture c on c.id = r.capture_id"
        " left join lateral (select human_read, judged from read_correction where item_result_id = r.id"
        " order by created_at desc limit 1) k on true"
        " where r.state in ('candidate', 'confirmed') and c.superseded_by is null"
        " and (%(i)s::uuid is null or r.item_id = %(i)s)",
        {"i": item_id},
    ).fetchall()
    learned, changed = learned_mistakes.rules(conn), []
    for r in (r for r in rows if r["judged"] is None and r["typed"] is not None):
        holds = (r["spec"] or {}).get("holds")
        right = marking._group(conn, r["capture_id"], holds, {})[r["id"]][2] if holds else False
        status, codes, working = marking._as_read(conn, r, r["typed"], right, learned)
        if status == r["status"]:
            continue
        try:
            with conn.transaction():  # a signed-off answer changes with its evidence, or not at all
                conn.execute(
                    "update item_result set status = %s, misconception_codes = %s, working_shown = %s,"
                    " updated_at = now() where id = %s",
                    (status, codes, working, r["id"]),
                )
                evidence = "select correct_signed_off(%s, %s) as n"
                if r["state"] == "confirmed" and not conn.execute(evidence, (r["id"], by)).fetchone()["n"]:
                    raise _Held
        except _Held:
            status = f"{r['status']} (held: {status} makes no evidence)"
        changed.append((r["item_key"], r["status"], status))
    return changed
