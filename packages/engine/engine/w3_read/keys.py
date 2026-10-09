"""W3/N9 — a paper question's right answer (goals/s26-the-right-answer-shown-and-corrected.yaml, ADR 0045).
- Shown as the engine stores it on every answer a person checks (`shown`).
- Changed by an educator for every child at once (`change`), once code has checked it (`check`).
- Kept as a row of its own that every entry of the paper puts back over its file (`reapply`).
- Every answer to the question is marked again by it (`again`).
Nimish, 2026-09-30: "the key can be changed by an educator, not an issue. also in any correction, the system should
show what the right answer is as stored in the system"."""

import json
import re

from engine.assess import misconceptions as M
from engine.w3_read import again, marking, naming

JUDGED = "a person judges this one"
LATEST = (
    "left join lateral (select was, by, created_at, answer from key_correction where tenant_id = i.tenant_id"
    " and item_key = i.item_key order by created_at desc limit 1) k on true"
)


def _key(item):
    """The right answer of an answer's own question part (`marking.response_of`): a stored result selects its own."""
    return marking.response_of(item).get("answer") if item["responses"] else None


def _right(item):
    """What an answer's card prints as its right answer."""
    spec, key = item["spec"] or {}, _key(item)
    if spec.get("holds"):
        return f"any answer that makes {re.sub(r'{(\w+)}', r'[\1]', spec['holds'])} true (the paper's own: {key})"
    return JUDGED if spec.get("kind") == "text" or key is None else str(key)


def shown(conn, paper_id):
    """Every answer on a paper (its capture, or the copy the Marking page shows) → {id, slot, right, was, by, at}: the
    right answer its card prints, as stored, and who changed it from what, if an educator did."""
    rows = conn.execute(
        "select r.id, i.item_key, i.spec, i.responses, result_response(i.responses, r.rid) as response, k.was, k.by,"
        " k.created_at as at from item_result r"
        f" join item i on i.id = r.item_id {LATEST} where {naming.ONE_PAPER}",
        (paper_id,),
    ).fetchall()
    return [
        {"id": str(r["id"]), "slot": r["item_key"].rsplit("/", 1)[-1], "right": _right(r)}
        | {"was": r["was"], "by": r["by"], "at": r["at"]}
        for r in rows
    ]


def check(item, answer):
    """The new right answer as it will be stored, or ValueError saying why code refuses it. What code can compute, it
    holds the answer to: a sum's arithmetic, an equation, and the form of the key it replaces."""
    spec, key, new = item["spec"] or {}, _key(item), (answer or "").strip()
    if spec.get("kind") == "text" or key is None:
        raise ValueError(
            f"{JUDGED}: whether each answer is right is a person's call, so it has no key to change"
        )
    if spec.get("holds"):
        raise ValueError(
            f"this box is marked by its equation, {spec['holds']}: any answer that makes its side come out is right"
        )
    if spec.get("op") and new != str(M.compute(spec["op"], spec["a"], spec["b"])):
        right = M.compute(spec["op"], spec["a"], spec["b"])
        raise ValueError(f"{spec['expr']} is {right}, so {new or 'nothing'} cannot be its right answer")
    truth = marking._truth(str(key))
    if truth is not None:
        if marking._truth(new) is None:
            raise ValueError(f"the right answer here is True or Not true, as {key} is")
        words = ("True", "Not true") if str(key).casefold() in ("true", "not true") else ("true", "false")
        new = words[0] if marking._truth(new) else words[1]
    elif re.fullmatch(r"-?\d+", str(key)) and not re.fullmatch(r"-?\d+", new):
        raise ValueError(f"the right answer here is a whole number, as {key} is")
    if not new:
        raise ValueError("say what the right answer is")
    if new == str(key):
        raise ValueError(f"{key} is the right answer already")
    return new


def _store(conn, item, answer):
    """The item's key, and what the misconceptions predict from it, as `legacy._template_item` makes them."""
    spec = {**(item["spec"] or {}), "answer": answer}
    response = {**item["responses"][0], "answer": answer, "misconceptions": M.predict_sign(answer)}
    conn.execute(
        "update item set spec = %s, responses = %s, updated_at = now() where id = %s",
        (json.dumps(spec), json.dumps([response, *item["responses"][1:]]), item["id"]),
    )


def change(conn, item_id, answer, by):
    """An educator's new right answer for one printed question, for every child → {was, now, changed, left, unseen}:
    checked (`check`), kept as a `key_correction` row, stored on the item, and every answer to it marked again
    (`again`): each change as (key, the mark it had, the mark it has), and each answer that keeps its mark though the new
    right answer disagrees, a person's call or a signed-off mark that makes no evidence, as (key, its mark, why). A
    library question's answer is code's; its wording is corrected in the Library instead."""
    item = conn.execute(
        "select id, tenant_id, item_key, spec, responses, source from item where id = %s", (item_id,)
    ).fetchone()
    if not item or item["source"] != "legacy":
        raise ValueError("only a paper's own question has a right answer to change here")
    new, key = check(item, answer), _key(item)
    conn.execute(
        "insert into key_correction (tenant_id, item_key, was, answer, by) values (%s, %s, %s, %s, %s)",
        (item["tenant_id"], item["item_key"], None if key is None else str(key), new, by),
    )
    _store(conn, item, new)
    typed, typed_left = again.mark_again(conn, by, item["id"])
    signed, signed_left = again.by_new_key(conn, by, item["id"], key)
    unseen = again.remark(conn, None, item["id"])  # what the reader read and no person has seen yet
    return {
        "was": str(key),
        "now": new,
        "changed": typed + signed,
        "left": typed_left + signed_left,
        "unseen": unseen,
    }


def change_from(conn, result_id, answer, by):
    """`change` for the question an answer is to: the Marking page changes a right answer on one child's answer."""
    row = conn.execute("select item_id from item_result where id = %s", (result_id,)).fetchone()
    if not row:
        raise ValueError(f"no answer with id {result_id}")
    return change(conn, row["item_id"], answer, by)


def reapply(conn, code):
    """Each question of paper `code` whose right answer an educator changed gets it back after the paper's file is
    entered again (every deploy, ADR 0043) → how many were put back."""
    rows = conn.execute(
        f"select i.id, i.spec, i.responses, k.answer from item i {LATEST} where i.item_key like %s and k.answer is not null",
        (f"legacy/{code}/%",),
    ).fetchall()
    for r in rows:
        if _key(r) != r["answer"]:
            _store(conn, r, r["answer"])
    return sum(_key(r) != r["answer"] for r in rows)
