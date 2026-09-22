"""W3/N9 — an answer marked against its question's key. The engine's own reading (`mark_read`: right
settles only once its kind is trusted, wrong and blank wait for a person — ADR 0029, 0032), a person's
reading (`correct`, a new `read_correction` row, the reader's own reading left untouched — rule 4),
and marking again when the rule changes (`remark`). `legacy.py` reads papers in; this marks them."""

import json
import re

from engine.assess import misconceptions as M
from engine.w3_read import profiles

# A typed or printed minus is the same minus; a multiplication "x" is a times sign.
_MINUS = str.maketrans({"−": "-", "–": "-", "x": "×"})


def normalise_answer(text):
    """What the child wrote, as a number string: '1,264' → '1264', '43 apples' → '43',
    'ans=43' → '43', '' stays ''. A read with digits tangled in other marks ('3?5') is returned
    as-is so it is marked unreadable rather than guessed at."""
    t = text.translate(_MINUS).replace(",", "").strip().rstrip(".")
    m = re.fullmatch(r"[^\d-]*(-?\d+)[A-Za-z₹.\s]*", t)
    return m.group(1) if m else t


def mark(spec, response, read):
    """→ (status, misconception codes, working_shown). Blank, wrong and wrong-with-working stay
    three signals (rule 5): status carries the first two, working_shown the third.

    `answer_state` (legacy_extract v3, ADR 0018) is the reader saying which of four different things
    it saw, rather than the caller inferring it from an empty string. v2 returned `attempted` and an
    empty `child_answer` for both "wrote nothing" and "wrote something I cannot read" — the exact
    collapse rule 5 forbids. `not_visible` is its own case because the SOF pages carry an educator's
    tick over a rubbed-out pencil mark: the outcome is knowable, the child's answer is not, and
    working backwards from the tick would invent an answer out of an adult's opinion of it.
    """
    working = read.get("working_shown") or ("partial" if read.get("working_summary") else "none")
    answer = normalise_answer(read.get("child_answer", ""))
    state = read.get("answer_state")
    if state == "blank":
        return "blank", [], working
    if state == "illegible":
        return "unreadable", [], working
    if state == "not_visible":
        return "needs_teacher", [], working
    if spec["kind"] == "text":
        if state == "blank" and not answer:
            return "blank", [], working
        # The judgement a "find the mistake" question asks for ("is Achal correct?") is not
        # checkable by code, but the number the child wrote beside it is — and ONLY when it agrees
        # with the key. Such a question prints its operands and the wrong answer, so its region
        # holds four or five numbers by construction and the reader is not entitled to say which
        # one the child stood behind: of fourteen such flags, five read the key exactly and the
        # other nine read a fragment ("2" where the answer is 75) or a printed operand. A
        # disagreement is therefore at least as likely to be the wrong number picked as a child
        # who is wrong, and marking it would buy coverage with silent errors — the one trade
        # rule 5 forbids. An agreement is two independent things saying the same thing, so it
        # settles; everything else still goes to a person.
        want = response.get("answer")
        if answer and want is not None and normalise_answer(str(want)) == answer:
            return "correct", [], working
        return "needs_teacher", [], working
    if not answer:
        return "needs_teacher", [], working
    want = response.get("answer")
    if want is not None and not re.fullmatch(r"-?\d+", str(want)):
        # The paper asks for something that is not one number — an order, a sign, a word. The
        # reader never reads these (`ocr.answers_for` hands them to a person without a guess), so
        # the reading here is a person's, and it is marked by the key's own form — and so is a
        # predicted wrong answer, the other comparison sign.
        wrote = read.get("child_answer", "")
        status = _against_the_key(str(want), wrote)
        predicted = response.get("misconceptions", {}).items()
        codes = [
            c for c, v in predicted if status == "wrong" and _against_the_key(str(v), wrote) == "correct"
        ]
        return status, sorted(codes), working
    if not re.fullmatch(r"-?\d+", answer):
        return "unreadable", [], working
    n = int(answer)
    if want is not None and n == int(want):
        return "correct", [], working
    codes = sorted(code for code, wrong in response.get("misconceptions", {}).items() if wrong == n)
    if not codes and want is not None:
        codes = sorted(code for code, (rule, _, _) in M.ANSWER_RULES.items() if rule(int(want), n))
    return "wrong", codes, working


# What the engine may not settle on its own reading (ADR 0029), and the reason it gives a person.
# A misread almost never lands on the exact key, so a right answer the reader read stands. A wrong or
# a blank is as often the reader's failure as the child's: of 30 the engine had settled alone, 9 were
# right answers it had not read — a first digit of 61, the top line of the working, an answer written
# beside the "=" instead of on the line (STATE.md, 2026-09-21).
# A kind of question with no checked readings yet has earned no trust (ADR 0032).
UNTRUSTED = {"n": 0, "right": 0, "trusted": False}


HELD = {
    "wrong": "read as a wrong answer; a person checks every wrong answer before it counts",
    "blank": "read as blank; a person checks every blank before it counts",
}


def mark_read(spec, response, read, gate=None):
    """`mark` for the ENGINE's own reading → (status, codes, working, read). A wrong or a blank waits for
    a person: the reading is kept, offered as the guess, and the reason is recorded where the queue
    reads it. A person's reading goes through `mark` itself — what a person says was written stands.

    `gate` is this kind of question's standing against `marking.agreement_gate` (ADR 0032,
    `profiles.kind_trust`): until the reader's readings of a kind have matched people 95% of the time
    over the last fifty checks, a right answer waits for a person too, its reading the one-click guess."""
    status, codes, working = mark(spec, response, read)
    if status == "correct" and gate and not gate["trusted"]:
        why = f"read as a right answer; a person checks every answer of this kind until the reader is trusted on it ({gate['right']} of the last {gate['n']} right)"
        return "needs_teacher", [], working, {**read, "why": why, "guess": read.get("child_answer", "")}
    if status not in HELD:
        return status, codes, working, read
    return "needs_teacher", [], working, {**read, "why": HELD[status], "guess": read.get("child_answer", "")}


def _against_the_key(key, wrote):
    """What a person says the child wrote, against a key that is not one number: numbers in order
    by the numbers in order ("12,34,45,78" is "12, 34, 45, 78"), a sign by the sign, and anything
    else — a word, a fraction — by its letters, ignoring case and spacing."""
    if re.fullmatch(r"\s*\d+(\s*[,;\s]\s*\d+)+\s*", key):
        # ponytail: a thousands comma inside a number ("1,234, 2,345") splits it alike on both sides;
        # a child who leaves that comma out would be marked wrong. No such key yet — split on the
        # key's own separator if one arrives.
        return "correct" if re.findall(r"\d+", wrote) == re.findall(r"\d+", key) else "wrong"
    if key.strip() in ("<", ">", "="):
        return "correct" if re.findall(r"[<>=]", wrote) == [key.strip()] else "wrong"
    same = re.sub(r"\s+", "", wrote).casefold() == re.sub(r"\s+", "", key).casefold()
    return "correct" if same else "wrong"


def correct(conn, result_id, human_read, by):
    """A person says what the child actually wrote. `POST /capture/correct`, and the mechanism the
    approval screen exists for.

    Append-only, and deliberately so (rule 4): the machine's own reading stays in
    `item_result.raw_read` untouched for ever, and the correction is a NEW `read_correction` row.
    Two things depend on that. A teacher can always see what the engine made of their child's
    handwriting, and the flag rate and the silent-error rate stay measurable afterwards — overwrite
    the read and the engine can never again be scored against the page it read.

    Only the MARK is recomputed, by the same `mark` the import path uses, because marking is a
    lookup against numbers computed when the paper was entered. A teacher is asked what a child
    wrote, never whether it is right.
    """
    row = conn.execute(
        "select r.id, r.tenant_id, r.raw_read, r.capture_id, si.child_id, i.spec, i.responses"
        " from item_result r join item i on i.id = r.item_id"
        " join capture c on c.id = r.capture_id join sheet_instance si on si.id = c.sheet_instance_id"
        " where r.id = %s and r.state = 'candidate'",
        (result_id,),
    ).fetchone()
    if not row:
        raise ValueError(f"no answer waiting for a person with id {result_id}")
    read = (
        json.loads(row["raw_read"] or "{}") if isinstance(row["raw_read"], str) else (row["raw_read"] or {})
    )
    text = (human_read or "").strip()
    reading = {**read, "child_answer": text, "answer_state": "written" if text else "blank"}
    status, codes, working = mark(row["spec"], row["responses"][0], reading)
    conn.execute(
        "insert into read_correction (tenant_id, child_id, capture_id, item_result_id, model_read,"
        " human_read, misconception_codes, by) values (%s,%s,%s,%s,%s,%s,%s,%s)",
        (
            row["tenant_id"],
            row["child_id"],
            row["capture_id"],
            row["id"],
            read.get("child_answer", "") or "",
            text,
            codes,
            by,
        ),
    )
    conn.execute(
        "update item_result set status = %s, misconception_codes = %s, working_shown = %s,"
        " updated_at = now() where id = %s",
        (status, codes, working, row["id"]),
    )
    return {"status": status, "codes": codes, "was": read.get("child_answer", "") or "", "now": text}


def corrections(conn):
    """Every answer a person has said the true reading of, latest first per answer.

    This is the gold set growing by use rather than by a data-entry project: a teacher confirming
    one paper hands the eval a handful of hand-verified responses, on the exact page a child wrote.
    """
    return conn.execute(
        "select distinct on (rc.item_result_id) t.batch_id as paper, c.path, c.pages as file_pages,"
        " coalesce((i.spec->>'page')::int, 1) as page, i.item_key, rc.human_read, rc.by, rc.created_at"
        " from read_correction rc"
        " join item_result r on r.id = rc.item_result_id"
        " join item i on i.id = r.item_id"
        " join capture c on c.id = rc.capture_id"
        " join sheet_instance si on si.id = c.sheet_instance_id"
        " join sheet_template t on t.id = si.sheet_template_id"
        " where c.superseded_by is null and rc.judged is null"  # a judgement is not a reading
        " order by rc.item_result_id, rc.created_at desc"
    ).fetchall()


def remark(conn, child_id):
    """Mark every candidate again from what was read, without asking the model again — for when
    the marking rule improves after a page was read. Returns how many rows changed.

    An answer a person has settled — typed what the child wrote, or judged it — is never marked again
    from the reader's own reading: that would put back the very reading the person corrected. Nor is
    a reading a later read superseded: it is history, and nothing else reads it either. A wrong or a
    blank the engine settled alone before ADR 0029 is held for a person here, its reading unchanged."""
    rows = conn.execute(
        "select r.id, r.raw_read, r.status, r.misconception_codes, r.working_shown, i.spec, i.responses, i.fmt"
        " from item_result r join item i on i.id = r.item_id"
        " join capture c on c.id = r.capture_id join sheet_instance si on si.id = c.sheet_instance_id"
        " where si.child_id = %s and r.state = 'candidate' and r.raw_read is not null"
        " and c.superseded_by is null"
        " and not exists (select 1 from read_correction rc where rc.item_result_id = r.id)",
        (child_id,),
    ).fetchall()
    changed = 0
    trust = profiles.kind_trust(conn)
    for r in rows:
        status, codes, working, read = mark_read(
            r["spec"], r["responses"][0], json.loads(r["raw_read"]), trust.get(r["fmt"], UNTRUSTED)
        )
        if (status, codes, working) != (r["status"], list(r["misconception_codes"]), r["working_shown"]):
            conn.execute(
                "update item_result set status = %s, misconception_codes = %s, working_shown = %s,"
                " raw_read = %s where id = %s",
                (status, codes, working, json.dumps(read), r["id"]),
            )
            changed += 1
    return changed


def confirm(conn, child_id, by):
    return conn.execute("select confirm_results(%s, %s) as n", (child_id, by)).fetchone()["n"]
