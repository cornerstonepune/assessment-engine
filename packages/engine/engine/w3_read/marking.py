"""W3/N9 — an answer marked against its question's key. The engine's own reading (`mark_read`: right
settles only once its kind is trusted, wrong and blank wait for a person — ADR 0029, 0032), a person's
reading (`correct`, a new `read_correction` row, the reader's own reading left untouched — rule 4).
Marking every answer again when its rule or key changes is `again.py`; `legacy.py` reads papers in."""

import hashlib
import json
import re

from engine.assess import equation
from engine.assess import learned_rules as L
from engine.assess import misconceptions as M
from engine.w1_bank import learned as learned_mistakes
from engine.w3_read import naming, profiles

# A typed or printed minus is the same minus; a multiplication "x" is a times sign.
_MINUS = str.maketrans({"−": "-", "–": "-", "x": "×"})


def normalise_answer(text):
    """What the child wrote, as a number string: '1,264' → '1264', '43 apples' → '43',
    'ans=43' → '43', '' stays ''. A read with digits tangled in other marks ('3?5') is returned
    as-is so it is marked unreadable rather than guessed at."""
    t = text.translate(_MINUS).replace(",", "").strip().rstrip(".")
    m = re.fullmatch(r"[^\d-]*(-?\d+)[A-Za-z₹.\s]*", t)
    return m.group(1) if m else t


def mark(spec, response, read, learned=()):
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
    if "text" in (
        spec.get("kind"),
        response.get("kind"),
    ):  # a paper's question, or a bank question's own answer
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
    if want is not None and _right_number(n, response):
        return "correct", [], working
    codes = sorted(code for code, wrong in response.get("misconceptions", {}).items() if wrong == n)
    if not codes and want is not None:
        codes = sorted(code for code, rule in M.ANSWER_RULES.items() if rule(int(want), n))
    if not codes and learned and L.works_the_sum(spec, response):
        # a mistake learned from children's answers and adopted by a person (goals/s22-learned-mistakes.yaml)
        codes = learned_mistakes.recognise(learned, spec.get("op"), int(spec["a"]), int(spec["b"]), n)
    return "wrong", codes, working


def _right_number(n, response):
    """`n` is the answer's key, or within the key's own tolerance where it has one (an estimate, `Response.tolerance`)."""
    return abs(n - int(response["answer"])) <= (response.get("tolerance") or 0)


def response_of(it):
    """The answer a slot is for: the one it names (`copies.paper` makes a slot per answer), else its question's first —
    a paper entered by hand asks for one answer a question. What a stored result is for is its own `rid`, read by
    `result_response` (migration 20261025090000) as every query that marks or shows one selects it."""
    return it.get("response") or it["responses"][0]


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


def spot_checked(capture_id, item_id, rate):
    """Whether a trusted kind's right answer is one a person still checks (step 4, `marking.spot_check_rate`): a
    fixed `rate` of them, chosen by the answer's own ids, so reading the same paper again picks the same ones."""
    h = hashlib.md5(f"{capture_id}/{item_id}".encode()).digest()
    return int.from_bytes(h[:8], "big") / 2**64 < rate


def spot_rate(conn):
    row = conn.execute("select value from threshold where key = 'marking.spot_check_rate'").fetchone()
    return float(row["value"]) if row else 0.15


def mark_read(spec, response, read, gate=None, spot=False, learned=()):
    """`mark` for the ENGINE's own reading → (status, codes, working, read). A wrong or a blank waits for
    a person: the reading is kept, offered as the guess, and the reason is recorded where the queue
    reads it. A person's reading goes through `mark` itself — what a person says was written stands.

    `gate` is this kind of question's standing against `marking.agreement_gate` (ADR 0032,
    `profiles.kind_trust`): until the reader's readings of a kind have matched people 95% of the time
    over the last fifty checks, a right answer waits for a person too, its reading the one-click guess. Once it
    is trusted, a right answer `spot` checked (`spot_checked`) still waits: the check that keeps the trust honest.

    A reading marked again starts from what the reader said: a hold an earlier marking put on it ("read as …", which a
    reader never writes — `profiles.doubted`) is not the reader's, so a hold lifted takes its reason and its guess with
    it, and the website stops showing the answer as waiting (`queries-read.held`)."""
    if (read.get("why") or "").startswith("read as"):
        read = {**read, "why": "", "guess": ""}
    status, codes, working = mark(spec, response, read, learned)
    if status == "correct" and gate and not gate["trusted"]:
        why = f"read as a right answer; a person checks every answer of this kind until the reader is trusted on it ({gate['right']} of the last {gate['n']} right)"
        return "needs_teacher", [], working, {**read, "why": why, "guess": read.get("child_answer", "")}
    if status == "correct" and spot:
        why = (
            "read as a right answer; spot-checked: a person checks a share of a trusted kind's right answers"
        )
        return "needs_teacher", [], working, {**read, "why": why, "guess": read.get("child_answer", "")}
    if status not in HELD:
        return status, codes, working, read
    return "needs_teacher", [], working, {**read, "why": HELD[status], "guess": read.get("child_answer", "")}


def verdicts(conn, capture_id):
    """`mark_read` for the readings of one capture: (item, reading) → (status, codes, working, reading), each held
    to its kind's standing (ADR 0032) and, once trusted, to the spot-check sample (step 4, `spot_checked`)."""
    trust, rate, learned = profiles.kind_trust(conn), spot_rate(conn), learned_mistakes.rules(conn)

    def judge(it, read):
        spot = spot_checked(capture_id, it["id"], rate)
        gate = trust.get(it["fmt"], UNTRUSTED)
        return mark_read(it["spec"], response_of(it), read, gate, spot=spot, learned=learned)

    return judge


# A claim is true or not true however a person types what the child ticked. The papers print "True" / "Not true", the
# bank's own questions say "true" / "false"; 2026-09-30, "false" typed for "odd + odd = odd" was marked wrong against
# the paper's "Not true" on every child's paper.
TRUTH: dict[str, bool] = {w: True for w in ("true", "t", "yes", "y", "✓", "✔", "tick")} | {
    w: False for w in ("nottrue", "false", "f", "no", "n", "untrue", "✗", "✘", "x", "cross")
}


def _truth(text):
    return TRUTH.get(re.sub(r"[\s.\-]+", "", text).casefold())


def _against_the_key(key, wrote):
    """What a person says the child wrote, against a key that is not one number: numbers in order
    by the numbers in order ("12,34,45,78" is "12, 34, 45, 78"), a sign by the sign, a claim by
    whether it says true (`TRUTH`), and anything else — a word, a fraction — by its letters,
    ignoring case and spacing."""
    if _truth(key) is not None:
        return "correct" if _truth(wrote) == _truth(key) else "wrong"
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
    wrote, never whether it is right. A box of one equation (`spec.holds`) is marked with the others
    of it: its side is right whatever split the child chose (`_group`).

    An answer already signed off is corrected the same way, and its evidence with it: a new batch in this
    person's name that the graph reads instead of the one before, which stays (`correct_signed_off`, migration
    20261015090000). A paper signed off by mistake is put right without editing a row.
    """
    row = conn.execute(
        "select r.id, r.tenant_id, r.raw_read, r.capture_id, r.state, si.child_id, i.spec, i.responses,"
        " result_response(i.responses, r.rid) as response from item_result r join item i on i.id = r.item_id"
        " join capture c on c.id = r.capture_id join sheet_instance si on si.id = c.sheet_instance_id"
        " where r.id = %s and r.state in ('candidate', 'confirmed')",
        (result_id,),
    ).fetchone()
    if not row:
        raise ValueError(f"no answer with id {result_id}")
    read, text = _read(row), (human_read or "").strip()
    learned, holds = learned_mistakes.rules(conn), (row["spec"] or {}).get("holds")
    group = _group(conn, row["capture_id"], holds, {row["id"]: text}) if holds else {}
    status, codes, working = _as_read(conn, row, text, group.get(row["id"], (row, text, False))[2], learned)
    conn.execute(
        # clock_timestamp(), not now(): two corrections in one transaction keep their order ("the latest" is exact)
        "insert into read_correction (tenant_id, child_id, capture_id, item_result_id, model_read,"
        " human_read, misconception_codes, by, created_at) values (%s,%s,%s,%s,%s,%s,%s,%s, clock_timestamp())",
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
    # the other boxes of its equation a person read, not yet signed off: this reading can make their side hold, or not.
    # One signed off changes only when a person saves it, with its evidence (`correct_signed_off`).
    marks = {row["id"]: (status, codes, working)} | {
        rid: _as_read(conn, b, typed, right, learned)
        for rid, (b, typed, right) in group.items()
        if rid != row["id"] and typed is not None and b["state"] == "candidate"
    }
    for rid, m in marks.items():
        conn.execute(
            "update item_result set status = %s, misconception_codes = %s, working_shown = %s,"
            " updated_at = now() where id = %s",
            (*m, rid),
        )
    if row["state"] == "confirmed":
        written = conn.execute("select correct_signed_off(%s, %s) as n", (row["id"], by)).fetchone()["n"]
        if not written:
            raise ValueError(
                f"{text or 'blank'} marks as {status}, which a signed-off answer cannot be changed to"
            )
    return {"status": status, "codes": codes, "was": read.get("child_answer", "") or "", "now": text}


def _read(row):
    raw = row["raw_read"]
    return json.loads(raw or "{}") if isinstance(raw, str) else (raw or {})


def _as_read(conn, row, typed, right, learned):
    """`mark` for what a person says the child wrote → (status, codes, working): right when the answer's side of its
    equation holds (`right`); a wrong answer keeps the mistake a person named on this very reading."""
    reading = {**_read(row), "child_answer": typed, "answer_state": "written" if typed.strip() else "blank"}
    status, codes, working = mark(row["spec"], response_of(row), reading, learned)
    if right:
        return "correct", [], working
    if status == "wrong" and not codes:  # a mistake a person named on this very reading still stands
        codes = naming.named(conn, row["id"], typed.strip())
    return status, codes, working


def _group(conn, capture_id, expr, now):
    """The boxes of one equation (`spec.holds`) on a paper → {result id: (row, what a person read in it or None, whether
    its side holds)}. A side holds when it comes out at the equation's total with what the child wrote — 600 + 19 + 19
    is 638 — as a person read it (`now`: {result id: the reading being saved}), or as the engine read it once it settled
    the box. A box still waiting for a person leaves its side undecided: each of its boxes is marked by its own key."""
    boxes = conn.execute(
        "select r.id, r.state, r.status, i.item_key, i.spec, i.responses, result_response(i.responses, r.rid) as response,"
        " r.raw_read, rc.human_read as typed"
        " from item_result r join item i on i.id = r.item_id left join lateral (select human_read from read_correction"
        " where item_result_id = r.id and judged is null order by created_at desc limit 1) rc on true"
        " where r.capture_id = %s and r.state <> 'rejected' and i.spec->>'holds' = %s",
        (capture_id, expr),
    ).fetchall()
    typed = {b["id"]: now.get(b["id"], b["typed"]) for b in boxes}
    name = {b["id"]: b["item_key"].rsplit("/", 1)[1] for b in boxes}
    wrote = {  # a person's reading, else the engine's once it settled the box; a box still waiting says nothing
        name[b["id"]]: typed[b["id"]] if typed[b["id"]] is not None else _read(b).get("child_answer") or ""
        for b in boxes
        if typed[b["id"]] is not None or b["status"] not in ("needs_teacher", "unreadable")
    }
    right = equation.right(expr, {k: normalise_answer(v) for k, v in wrote.items()})
    return {b["id"]: (b, typed[b["id"]], bool(right.get(name[b["id"]]))) for b in boxes}


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


def confirm(conn, child_id, by):
    return conn.execute("select confirm_results(%s, %s) as n", (child_id, by)).fetchone()["n"]
