"""The skill-set spec: what a person approves, and the mistake list the engine derives for it.

Two halves, deliberately separated (CLAUDE.md: code where correctness is needed, a model where
judgment is needed):

* **Code owns what code can compute.** Run the predictors over the numbers a band's own rule allows
  and you have, exactly and for nothing, every named wrong method reachable in that band. No model
  is asked to remember a list that arithmetic can produce.
* **The model owns what code cannot.** How a child misreads a story, what they do with the wrong
  two numbers out of three, a method nobody has written a predictor for. It is told what code has
  already covered, so it spends its answer on the rest.

Every proposal is then checked before anything is stored, and a claim that cannot be verified is
downgraded rather than trusted (ADR 0014).
"""

import random
import re

from engine.adapters import llm
from engine.assess import bands, draw
from engine.assess import misconceptions as M
from engine.core import db
from engine.w1_bank import cases

MISCONCEPTION_PROMPT = "misconception_list"
FACT_SLIPS = ("M_FACT_PM1", "M_FACT_PM10")
SAMPLE_PAIRS = 40  # per band: enough that a rare regrouping shape appears, cheap because it is free


def row(conn, code):
    s = conn.execute("select * from skill_set where code = %s", (code,)).fetchone()
    if not s:
        raise ValueError(f"no skill set {code!r}")
    return s


def read(conn, code, difficulty):
    """One band's spec as the item-generation prompt's input, built only from rows: skill set, rung, school philosophy, misconceptions."""
    s = conn.execute(
        "select s.*, r.band, r.skill_codes from skill_set s"
        " join rung r on r.tenant_id = s.tenant_id and r.code = s.rung_code where s.code = %s",
        (code,),
    ).fetchone()
    if not s:
        raise ValueError(f"no skill set {code!r}")
    band = s["difficulty"].get(difficulty)
    if not band:
        raise ValueError(f"{code} has no difficulty {difficulty!r}; it has {', '.join(s['difficulty'])}")
    school = conn.execute("select value from config where key = 'assessment.philosophy'").fetchone()
    mis = conn.execute(
        "select distinct on (code) code, description from misconception where code = any(%s) order by code",
        (list(s["misconception_codes"]),),
    ).fetchall()
    prompt_input = {
        "topic": s["name"],
        "skill": f"{s['rung_code']} — {', '.join(s['skill_codes'])}",
        "learning_objective": s["learning_objective"],
        "difficulty": f"{difficulty}: {band['words']}",
        "philosophy": list(school["value"] if school else []) + list(s["philosophy"]),
        "formats": list(s["formats"]),
        "misconceptions": [{"code": m["code"], "description": m["description"]} for m in mis],
    }
    return prompt_input, s, band["check"]


def ratify(conn, actor, code=None):
    """N1's human gate, recorded: a named person has read these specs and stands behind them.
    Editing a spec afterwards withdraws its ratification (trigger skill_set_version_on_change),
    so a ratification always refers to the exact words that were read."""
    return conn.execute(
        "update skill_set set status = 'ratified', ratified_by = %s, updated_at = now()"
        " where status = 'draft' and (%s::text is null or code = %s)"
        " returning code, version",
        (actor, code, code),
    ).fetchall()


# A skill on the map is what the child can do, said the way a teacher says it — never a topic label
# ("2-digit addition with regrouping"), never the engine's own vocabulary. Nimish, 2026-09-21: "the
# outcome needs to be articulated as a skill". Checked by `engine spec outcomes`.
OUTCOME_WORDS = (8, 30)
NOT_A_TEACHERS_WORD = (
    "rung",
    "misconception",
    "misconceptions",
    "planted",
    "predictor",
    "borrow",
    "borrowing",
    "algorithm",
)
_CODE = re.compile(r"\b[A-Z]{2,}[._][A-Z0-9_.]+\b|\bM_[A-Z_]+\b|\b[RXM]\d{1,2}\b")


def outcome_problems(text):
    """Why this sentence is not yet an outcome — nothing when it is one."""
    problems = []
    words = text.split()
    first = words[0] if words else ""
    if not (first[:1].isupper() and first.isalpha() and first.endswith("s")):
        problems.append(f"does not start with what the child does (a verb such as Adds), it starts {first!r}")
    if not text.rstrip().endswith(".") or re.search(r"[.!?]\s+[A-Z]", text):
        problems.append("is not one sentence ending in a full stop")
    lo, hi = OUTCOME_WORDS
    if not lo <= len(words) <= hi:
        problems.append(f"has {len(words)} words, not {lo}–{hi}")
    if _CODE.search(text):
        problems.append(f"names a code ({_CODE.search(text).group(0)})")
    said = {w.strip(".,;:()'\"").lower() for w in words}
    problems += [f"uses the engine's word {w!r}" for w in NOT_A_TEACHERS_WORD if w in said]
    return problems


def outcomes(conn):
    """Every skill set's outcome and what is wrong with it, in ladder order."""
    rows = conn.execute(
        "select s.code, s.learning_objective from skill_set s"
        " join rung r on r.tenant_id = s.tenant_id and r.code = s.rung_code order by r.ladder_order, s.code"
    ).fetchall()
    return [(r["code"], r["learning_objective"], outcome_problems(r["learning_objective"])) for r in rows]


def known_misconceptions(conn, code, n=SAMPLE_PAIRS):
    """{difficulty: [codes]} — what the predictors actually produce on each band's own numbers.

    This is the deterministic half of the mistake list. A band whose rule forbids exchange cannot
    reach an exchange mistake and will not list one; a native-generator band (an explanation, a
    budget) has no numbers to sample and comes back empty, which is the honest answer rather than
    a guess.
    """
    s = row(conn, code)
    out = {}
    for d, b in s["difficulty"].items():
        check = b.get("check") or {}
        if check.get("cases"):
            # A level made of taxonomy cases: the mistakes its own drawn questions can show (step 8f).
            drawn = draw.level(
                random.Random(1), check, cases.matches(conn, check["cases"]), s["rung_code"], n
            )
            out[d] = sorted({c for _, it in drawn for r in it.responses for c in (r.misconceptions or {})})
        else:
            out[d] = bands.codes(check, n, rung=s["rung_code"])
    return out


# Words that carry no meaning in a code. A join key is read by people — in a graph, a prescription,
# a teacher's screen — so it is three words long, not a sentence with its spaces replaced.
_FILLER = {
    "THE",
    "A",
    "AN",
    "OF",
    "THAT",
    "THIS",
    "DOES",
    "DOESNT",
    "NOT",
    "BECAUSE",
    "IS",
    "ARE",
    "IN",
    "ON",
    "FOR",
    "TO",
    "AS",
    "AND",
    "OR",
    "WITH",
    "FROM",
    "ITS",
    "IT",
    "S",
    "BY",
    "AT",
    "WHEN",
    "ONLY",
    "ALL",
    "ANY",
    "THEN",
    "THEIR",
    "THEM",
    "HAS",
    "HAVE",
    "BEEN",
    "BUT",
    "SO",
    "INTO",
}


def _code_for(name):
    """A stable, readable code from a proposed mistake's name: `M_` plus its first three words that
    mean something. Mechanical, never the model's invention — and short, because the first version
    slugged whole sentences and produced `M_MISREAD_THE_QUESTION_S_DEMAND_ANSWERED_THE_Q`, which the
    graph and every screen would have carried from then on.
    """
    letters = "".join(c if c.isalnum() else " " for c in name.split("(")[0].split(":")[0].upper())
    words = [w for w in letters.split() if w not in _FILLER and not w.isdigit()]
    if not words:
        return "M_UNNAMED"
    out = []
    for w in words[:3]:
        if len("_".join(out + [w])) > 28:  # whole words only: a code cut mid-word reads as a typo
            break
        out.append(w)
    return "M_" + "_".join(out or [words[0][:28]])


def _same_wrong_path(predicted, written):
    """Which known misconceptions produce exactly this wrong answer. A fact slip lands on the same
    number as a real procedural mistake often enough to be noise — 62 - 27 as 45 is both "forgot to
    reduce the tens" and "ten out on the fact" — so it is reported only when nothing structural
    explains the answer. Two structural methods that agree are both kept: the answer alone cannot
    separate them, and the child's written working is what finally does.
    """
    same = sorted(c for c, v in predicted.items() if v == written)
    structural = [c for c in same if c not in FACT_SLIPS]
    return structural or same


def expression(example):
    """`305 - 127` or `4321 + 2456 + 3212` — the question a proposal's example asks, for a person."""
    return f" {example['op']} ".join(str(n) for n in example["numbers"])


def _check_proposal(m, covered):
    """One proposal, judged by arithmetic alone. Sets exactly one of dropped / matches / new, and
    downgrades a claim code cannot support instead of storing it as if it could."""
    ex = m.get("example")
    p = {**m, "code": _code_for(m["name"]), "matches": [], "dropped": None, "downgraded": None}
    if not ex:
        # A mistake in reasoning or in an explanation has no wrong number, so there is nothing to
        # check and nothing a marker can look up. Demanding arithmetic for it only invites invented
        # arithmetic, which is what the first two prompt versions got.
        if p["visible_in"] == "answer_lookup":
            p["downgraded"] = "no example answer, so it cannot be marked from the answer alone"
            p["visible_in"] = "explanation"
        return p
    nums, op = list(ex["numbers"]), ex["op"]
    try:
        correct = M.chain(op, nums)
    except KeyError:
        correct = None  # an operation with no arithmetic here: nothing to check, nothing claimed
    if correct is not None and ex.get("correct_answer", correct) != correct:
        # The model stated the right answer wrongly, so its wrong answer proves nothing. This keeps
        # "did not name the mistake" apart from "named it and miscounted".
        p["dropped"] = f"its own arithmetic is wrong: {expression(ex)} is {correct}"
        return p
    if correct is not None and ex["child_writes"] == correct:
        p["dropped"] = "its example's wrong answer is the right answer"
        return p
    predicted = M.predict_multi(nums) if len(nums) > 2 else M.predict(op, nums[0], nums[1])
    p["matches"] = _same_wrong_path(predicted, ex["child_writes"])
    if p["matches"]:
        p["already_covered"] = bool(set(p["matches"]) & set(covered))
        return p
    if p["visible_in"] == "answer_lookup":
        # Nothing computes this answer, so "you can see it in the answer alone" is a claim no marker
        # can act on. It becomes a mistake a person reads in the working — until someone writes the
        # predictor that reproduces it, which is what would make the stronger claim true.
        p["downgraded"] = "no predictor reproduces this answer, so it cannot be marked from the answer alone"
        p["visible_in"] = "working"
    return p


def apply_computed(conn, code, n=SAMPLE_PAIRS):
    """Union into a spec exactly what code can already mark against — no model, no cost.

    A spec that lists fewer mistakes than the engine computes is not wrong, it is out of date: the
    marker is already diagnosing children with mistakes the document never mentions (67 of them
    across the ladder when this was written). Returns the codes added.
    """
    s = row(conn, code)
    computed = {c for codes in known_misconceptions(conn, code, n).values() for c in codes}
    added = sorted(computed - set(s["misconception_codes"]))
    if added:
        conn.execute(
            "update skill_set set misconception_codes = %s where code = %s",
            (sorted(set(s["misconception_codes"]) | computed), code),
        )
    return added


def propose_misconceptions(conn, code, apply=False, meta=None, n=SAMPLE_PAIRS):
    """The whole mistake list for one skill set: what code computes, plus what only judgment finds.

    Returns {"known": {band: [codes]}, "covered": [codes], "proposals": [...]}. Nothing is written
    unless `apply`, and applying unions — it can never remove a code a person curated.
    """
    s = row(conn, code)
    meta = meta if meta is not None else {}  # provenance is recorded whether or not a caller wants it
    known = known_misconceptions(conn, code, n)
    covered = sorted({c for codes in known.values() for c in codes})
    names = {
        r["code"]: r["name"]
        for r in conn.execute(
            "select distinct on (code) code, name from misconception order by code"
        ).fetchall()
    }
    variables = {
        "skill_set": {
            "code": s["code"],
            "name": s["name"],
            "learning_objective": s["learning_objective"],
            "philosophy": list(s["philosophy"]),
            "formats": list(s["formats"]),
        },
        "bands": {d: b.get("words", "") for d, b in s["difficulty"].items()},
        # Everything the vocabulary already names, not only what this band computes: a mistake in
        # reading a story has no wrong number to match on, so showing the model the existing name is
        # the only thing that stops a second name for it.
        "already_covered": sorted(set(names.values())),
    }
    out = llm.generate(conn, MISCONCEPTION_PROMPT, variables, meta=meta)
    proposals = [_check_proposal(m, covered) for m in out["mistakes"]]
    if apply:
        _store(conn, s, covered, proposals, meta)
    return {"known": known, "covered": covered, "proposals": proposals}


def _store(conn, s, covered, proposals, meta):
    """New rows for the genuinely new, then the union attached to the skill set. Attaching is a
    content edit, so the versioning trigger withdraws the set's ratification — correct: the person
    signs the list they were shown, and a changed list has not been signed."""
    tenant = conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]
    source = f"{MISCONCEPTION_PROMPT} · {meta.get('model') or 'model'} · prompt {meta.get('prompt_id')}"
    codes = set(s["misconception_codes"]) | set(covered)
    for p in proposals:
        if p["dropped"]:
            continue
        if p["matches"]:
            codes.update(p["matches"])
            continue
        ex = p.get("example") or {}
        op = ex.get("op") if ex.get("op") in ("+", "-") else "any"  # "×" and no-example share 'any'
        note = p["how_it_goes"] + (f" [{p['downgraded']}]" if p["downgraded"] else "")
        conn.execute(
            "insert into misconception (tenant_id, code, op, name, description, repair_hint,"
            " detectable_by, source) values (%s,%s,%s,%s,%s,%s,%s,%s)"
            " on conflict (tenant_id, code, op) do nothing",
            (tenant, p["code"], op, p["name"], note, p["repair_hint"], p["visible_in"], source),
        )
        codes.add(p["code"])
    conn.execute("update skill_set set misconception_codes = %s where code = %s", (sorted(codes), s["code"]))


def evaluate_misconception_list(conn, codes):
    """The eval for the prompt (rule 7), scored on the job the prompt actually has now.

    What code computes is not the prompt's credit and is reported separately as `covered`. The
    prompt is measured on what it adds: proposals that survive the arithmetic check, are not already
    covered, and make a claim code can support — and on how many it wastes on each of those.
    """
    rows, cost, model = [], 0.0, None
    for code in codes:
        meta = {}
        r = propose_misconceptions(conn, code, apply=False, meta=meta)
        ps = r["proposals"]
        cost += meta.get("cost_inr") or 0
        model = meta.get("model") or model
        rows.append(
            {
                "code": code,
                "covered": len(r["covered"]),
                "proposed": len(ps),
                "dropped": sum(1 for p in ps if p["dropped"]),
                "already": sum(1 for p in ps if p["matches"]),
                "new": sum(1 for p in ps if not p["matches"] and not p["dropped"]),
                "downgraded": sum(1 for p in ps if p["downgraded"]),
            }
        )
    proposed = sum(r["proposed"] for r in rows) or 1
    return {
        "rows": rows,
        "model": model,
        "cost_inr": round(cost, 4),
        "useful": round(sum(r["new"] for r in rows) / proposed, 2),
    }
