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

from engine import bank, db, scenarios_week, spec
from engine.assess import bands, tags, taxonomy, verify
from engine.assess import misconceptions as M

CHECKS = ("produced", "answers", "on_rule", "diagnostic", "unique")


def _vocabulary(conn):
    return {r["code"] for r in conn.execute("select distinct code from misconception").fetchall()}


def _answer_is_right(item):
    """Recompute from the numbers in the question, never trusting the stored answer."""
    s = item.spec or {}
    nums = s.get("addends") or ([s["a"], s["b"]] if {"a", "b"} <= s.keys() else None)
    if not nums or not s.get("op"):
        return None  # a question with no arithmetic of its own (a story, an explanation)
    want = sum(nums) if s["op"] == "+" and len(nums) > 2 else M.compute(s["op"], nums[0], nums[1])
    if s.get("missing"):
        return None  # a missing-number question's answer is an operand, checked by its own rule
    stated = next((r.answer for r in item.responses if r.rid in ("ans", "answer")), None)
    return None if stated is None else str(want) == str(stated).strip()


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
    if native:
        counts, items = bank.fill_native(conn, code, difficulty, n, dry_run=True)
    else:
        counts, reasons, items = bank.fill(conn, code, difficulty, n, dry_run=True, offline=True)
        counts = dict(counts, rejected_because=dict(reasons))
    conn.rollback()  # a scenario proves the engine, it does not add to the bank

    vocab = _vocabulary(conn)
    m = {"asked": n, "produced": len(items)}
    failures = []
    if len(items) < n:
        failures.append(
            f"produced {len(items)} of {n} asked"
            + (f" · rejected for {counts.get('rejected_because')}" if counts.get("rejected_because") else "")
        )

    wrong_answer, off_rule, undiagnosed = [], [], []
    for it in items:
        ok = _answer_is_right(it)
        if ok is False:
            wrong_answer.append(it.item_id)
        problems = verify.dimension_problems(tags.derive(it), check)
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
        "answers_recomputed": len(items) - len(wrong_answer),
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
        rows = conn.execute("select code, match from taxonomy_case where code = any(%s)", (sc["cases"],)).fetchall()
        match = {r["code"]: r["match"] for r in rows}
        measured = [(it.fmt, tags.derive(it)) for it in items]
        absent = [c for c in sc["cases"] if c not in match or not any(taxonomy.matches(match[c], f, t) for f, t in measured)]
        m["cases_held"] = len(sc["cases"]) - len(absent)
        if absent:
            failures.append(f"cases the level should hold and the set does not: {absent}")
    return m, failures


def run(scenarios, conn=None):
    if conn is None:
        with db.connect() as own:
            return [(sc, *run_one(own, sc)) for sc in scenarios]
    return [(sc, *run_one(conn, sc)) for sc in scenarios]
