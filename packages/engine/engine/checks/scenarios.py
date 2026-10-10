"""Does the engine actually do its job? `engine goal <name>` runs these.

A scenario states a real request in the school's terms — this topic, this difficulty, this many
questions — and then checks the questions that come back, independently of the code that made them:
every answer recomputed from the numbers, every question re-measured against the band's own rule,
every wrong answer mapped to a named mistake, no two questions the same. Nothing is stored.

Nimish, 2026-09-20: "If the assessment engine's goal is to build the set of questions for given
difficulties for a given task, with a set of conditions for a subject, the system should be able to
test that across a couple of scenarios … till 100% accuracy is achieved."

100% is the bar on purpose: a scenario that produces 19 of 20 asked-for questions, or 20 whose
distractors include one unnamed code, has not met the goal. The number it reports is what fails.
"""

import re

from engine.assess import bands, tags, taxonomy, verify
from engine.assess import md_tags as MD
from engine.assess import misconceptions as M
from engine.assess import operations as O
from engine.checks import scenarios_week
from engine.core import db
from engine.w1_bank import bank, cases, refill, spec

CHECKS = ("produced", "answers", "on_rule", "diagnostic", "unique")


def _vocabulary(conn):
    return {r["code"] for r in conn.execute("select distinct code from misconception").fetchall()}


def _from_sentence(sentence):
    """The one number a printed sentence's box stands for: a × or ÷ sentence worked as the tags read it
    (`md_tags.solved`), "28 ÷ 4 = □" 7, "6 × □ = 42" 7, "□ × □ = 49" 7, "60 × 7 =" 420; a digit among a division's
    digits (`_digit`); a check worked left to right, × first ("21 × 4 + 2 = □" is 86); None for any other sentence."""
    text = sentence.strip()
    worked = _worked(text)
    if worked is not None:
        return worked
    if "□" in text and not re.search(r"(^|\s)□(\s|$)", text):
        return _digit(text)
    sp = MD.solved({"text": f"{text} □" if text.endswith("=") else text})
    hide, a, b = sp.get("missing"), sp.get("a"), sp.get("b")
    if hide in ("a", "both"):
        return a
    if hide == "b":
        return b
    if hide in ("answer", "remainder") and isinstance(a, int) and isinstance(b, int):
        q, r = O.divide(a, b) if sp["op"] == "÷" else (a * b, 0)
        return r if hide == "remainder" else (None if r else q)
    return None


def _answer_is_right(item):
    """Recompute from the question as it is printed, never trusting the stored answer: a sum from its numbers (a
    division's quotient, and its remainder in a box of its own only where there is one, ADR 0056); a missing number from
    its sentence; and every box printed after a sentence of its own ("28 ÷ 4 = □", "60 × 7 =") from that sentence.
    None when nothing in it can be worked: an explanation, boxed digits, a story with no numbers of its own."""
    s = item.spec or {}
    stated = {r.rid: str(r.answer).strip() for r in item.responses if r.answer is not None}
    checks = [
        _same(stated.get(r.rid), want)
        for r in item.responses
        if r.label and (want := _from_sentence(r.label)) is not None
    ]
    # a question printed as a sentence with a box is that sentence's, never the sum of its two numbers: □ − 14 = 8,
    # found wrong as 6, is 22, and was read as 22 − 14
    if item.fmt == "missing_number" or "□" in (s.get("text") or ""):
        want = _from_sentence(s.get("text") or "")
        box = "d1" if item.fmt == "missing_digit" else "ans"
        checks += [] if want is None else [_same(stated.get(box), want)]
    elif (whole := _sum_is_right(s, stated)) is not None:
        checks.append(whole)
    if item.fmt == "estimate_then_calc" and "est" in stated and (est := _estimate(s)) is not None:
        checks.append(_same(stated["est"], est))
    if (tick := _ticks(item.fmt, s, stated)) is not None:
        checks.append(tick)
    return all(checks) if checks else None


def _worked(text):
    """A sentence asking what a calculation of + − × makes ("605 − 258 = □", "21 × 4 + 2 = □"), worked with × before
    + and −; None for any other sentence."""
    m = re.fullmatch(r"(\d+(?:\s*[+−×-]\s*\d+)+)\s*=\s*□?", text)
    if not m or not re.search(r"[+−-]", m[1]):
        return None  # a × or ÷ alone is `md_tags.solved`'s, which reads its boxes too
    terms = re.split(r"\s*([+−-])\s*", m[1])
    value = 0
    for sign, term in zip(["+", *terms[1::2]], terms[0::2], strict=True):
        part = 1
        for f in re.split(r"\s*×\s*", term):
            part *= int(f)
        value += part if sign == "+" else -part
    return value


def _digit(text):
    """The one digit that makes a printed division with a box among a number's digits true, its remainder less than its
    divisor: "7□ ÷ 4 = 18" is 2, "936 ÷ 3 = 3□2" is 1. None when the sentence is no such division, or when no digit or
    more than one fits: a box two digits fit is no question."""
    m = re.fullmatch(r"(\S+) ÷ (\S+) = (\S+)(?: r (\S+))?", text)
    if not m or text.count("□") != 1:
        return None
    fits = []
    for d in range(10):
        parts = [x.replace("□", str(d)) for x in m.groups() if x is not None]
        if not all(x.isdigit() and (len(x) == 1 or x[0] != "0") for x in parts):
            continue
        a, b, q, r = [int(x) for x in parts] + [0] * (4 - len(parts))
        if b and a == q * b + r and r < b:
            fits.append(d)
    return fits[0] if len(fits) == 1 else None


def _half_up(n, to):
    return (n + to // 2) // to * to


def _estimate(s):
    """An estimate's first box, from the rounding its question states: a + or − rounds both numbers to its `round_to`;
    a × the larger number, or both, to the ten, or asks the product's digits or its last digit; a ÷ the number divided
    to the hundred, or the quotient's digits. None where the question states none of these."""
    a, b, op, shape = s.get("a"), s.get("b"), O.sign(s.get("op")), s.get("shape")
    if not (isinstance(a, int) and isinstance(b, int) and b):
        return None
    if op == "÷":
        hundred = _half_up(a, 100)
        if shape == "ROUND_ONE":
            return hundred // b if hundred % b == 0 else None
        return len(str(a // b)) if shape == "ANSWER_DIGITS" else None
    if op == "×":
        big, small = max(a, b), min(a, b)
        return {
            "ROUND_ONE": _half_up(big, 10) * small,
            "ROUND_BOTH": _half_up(a, 10) * _half_up(b, 10),
            "ANSWER_DIGITS": len(str(a * b)),
            "LAST_DIGIT": a * b % 10,
        }.get(shape)
    to = s.get("round_to", 10)
    return M.compute(op, _half_up(a, to), _half_up(b, to)) if op in ("+", "-") else None


def _claim_is_right(s):
    """Whether the answer a question claims for its sum is its answer: "21 r 1" for 85 ÷ 4, 605 for 347 + 258. None
    where it claims none."""
    claimed, a, b, op = s.get("claimed"), s.get("a"), s.get("b"), O.sign(s.get("op"))
    if claimed is None or not (isinstance(a, int) and isinstance(b, int)):
        return None
    m = re.fullmatch(r"(\d+)(?: r (\d+))?", str(claimed).replace(",", ""))
    if not m:
        return None
    if op == "÷":
        return b > 0 and (int(m[1]), int(m[2] or 0)) == O.divide(a, b)
    return m[2] is None and int(m[1]) == M.compute(op, a, b)


def _ticks(fmt, s, stated):
    """A judged claim's tick, worked from the claim: "Could it be right?" is yes for a remainder less than its divisor
    (and, for + and −, the answer itself); "Is the answer right?" yes for the answer. None for any other question."""
    right = _claim_is_right(s)
    if right is None:
        return None
    if fmt == "possible_answer" and "could" in stated:
        if O.sign(s.get("op")) == "÷":
            m = re.fullmatch(r"(\d+) r (\d+)", str(s["claimed"]))
            right = bool(m) and int(m[2]) < s["b"]
        return stated["could"] == ("yes" if right else "no")
    if fmt == "inverse_check" and "right" in stated:
        return stated["right"] == ("yes" if right else "no")
    return None


def _same(stated, want):
    """A box's answer is the number worked out: a lattice's cell keyed "03" for 3 × 1 is 3."""
    return stated is not None and (stated.isdigit() and int(stated) == want or stated == str(want))


# What a story that divides asks of its division (goals/md3b3-divide-mistakes-and-stories.yaml), worked here apart from
# the code that wrote the story: the full groups, one more for those left over, what is left over, or both.
USED = {
    "ROUND_DOWN": lambda q, r: (q, None),
    "ROUND_UP": lambda q, r: (q + (1 if r else 0), None),
    "REMAINDER_ASKED": lambda q, r: (r, None),
    "BOTH_ASKED": lambda q, r: (q, r),
}


def _sum_is_right(s, stated):
    """The question's own sum, recomputed from its numbers, against its answer's box; None where it has no sum."""
    nums = s.get("addends") or ([s["a"], s["b"]] if {"a", "b"} <= s.keys() else None)
    if not nums or not s.get("op") or not all(isinstance(x, int) for x in nums):
        return None  # a question with no arithmetic of its own (a story, an explanation, boxed digits)
    if O.sign(s["op"]) == "÷":
        if "ans" not in stated:
            return None  # a claim judged or checked: its ticks and boxes are worked on their own (`_ticks`)
        ans, rem = USED.get(s.get("remainder_use"), lambda q, r: (q, r or None))(*divmod(nums[0], nums[1]))
        return stated.get("ans") == str(ans) and stated.get("rem") == (None if rem is None else str(rem))
    want = sum(nums) if s["op"] == "+" and len(nums) > 2 else M.compute(s["op"], nums[0], nums[1])
    answer = stated.get("ans", stated.get("answer"))
    return None if answer is None else str(want) == answer


def run_one(conn, sc):
    kind = sc.get("kind", "bank")
    if kind == "week":
        return scenarios_week.run(conn, sc)
    if kind != "bank":
        return {"kind": kind}, [f"no runner for a {kind!r} scenario yet — this goal is declared, not met"]
    return _run_bank(conn, sc)


def _run_bank(conn, sc):
    """One scenario → (measurements, failures). Nothing is written to the database."""
    code, difficulty, n = sc["skill_set"], sc["difficulty"], int(sc.get("n", 20))
    _, s, check = spec.read(conn, code, difficulty)
    native = check.get("format") in bands.NATIVE_GENERATORS
    if check.get("cases"):
        counts, _, items = refill.fill_cases(conn, code, difficulty, n, dry_run=True)
    elif native:
        counts, items = bank.fill_native(conn, code, difficulty, n, dry_run=True)
    else:
        counts, reasons, items = bank.fill(conn, code, difficulty, n, dry_run=True, offline=True)
        counts = dict(counts, rejected_because=dict(reasons))
    conn.rollback()  # a scenario proves the engine, it does not add to the bank

    vocab = _vocabulary(conn)
    case_matches = cases.matches(conn) if check.get("cases") else None
    m = {"asked": n, "produced": len(items)}
    failures = []
    if len(items) < n:
        failures.append(
            f"produced {len(items)} of {n} asked"
            + (f" · rejected for {counts.get('rejected_because')}" if counts.get("rejected_because") else "")
        )

    wrong_answer, off_rule, undiagnosed, worked = [], [], [], []
    for it in items:
        ok = _answer_is_right(it)
        worked.append(ok)
        if ok is False:
            wrong_answer.append(it.item_id)
        problems = verify.dimension_problems(tags.derive(it), check, it.fmt, case_matches)
        if problems:
            off_rule.append(f"{it.item_id}: {','.join(problems)}")
        named = {c for r in it.responses for c in (r.misconceptions or {}) if c in vocab}
        unnamed = {c for r in it.responses for c in (r.misconceptions or {})} - vocab
        if unnamed:
            undiagnosed.append(f"{it.item_id}: {','.join(sorted(unnamed))} not in the vocabulary")
        elif not named and not sc.get("allow_no_distractors"):
            undiagnosed.append(f"{it.item_id}: no named mistake to mark against")
    keys = [it.item_id for it in items]
    m |= {
        "answers_recomputed": worked.count(True) + worked.count(False),
        "answers_with_nothing_to_work": worked.count(
            None
        ),  # an explanation, boxed digits: counted, never as worked
        "off_rule": len(off_rule),
        "undiagnosed": len(undiagnosed),
        "distinct": len(set(keys)),
    }
    if wrong_answer:
        failures.append(f"{len(wrong_answer)} answers disagree with the arithmetic: {wrong_answer[:3]}")
    if off_rule:
        failures.append(f"{len(off_rule)} questions outside the band's own rule: {off_rule[:3]}")
    if undiagnosed:
        failures.append(f"{len(undiagnosed)} questions nothing could diagnose: {undiagnosed[:3]}")
    if len(set(keys)) != len(keys):
        failures.append(f"{len(keys) - len(set(keys))} duplicate questions in one set")
    if sc.get("cases"):
        # Re-measured from the questions and read against the case rows, not asked of the generator.
        rows = conn.execute(
            "select code, match from taxonomy_case where code = any(%s)", (sc["cases"],)
        ).fetchall()
        match = {r["code"]: r["match"] for r in rows}
        measured = [(it.fmt, tags.derive(it)) for it in items]
        absent = [
            c
            for c in sc["cases"]
            if c not in match or not any(taxonomy.matches(match[c], f, t) for f, t in measured)
        ]
        m["cases_held"] = len(sc["cases"]) - len(absent)
        if absent:
            failures.append(f"cases the level should hold and the set does not: {absent}")
    return m, failures


def run(scenarios, conn=None):
    if conn is None:
        with db.connect() as own:
            return [(sc, *run_one(own, sc)) for sc in scenarios]
    return [(sc, *run_one(conn, sc)) for sc in scenarios]
