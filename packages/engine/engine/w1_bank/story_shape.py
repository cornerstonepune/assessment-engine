"""A story question in anyone's words → its shape, its taxonomy case, where it sits, and — for one step — its answer
(goals/j3-story-shape.yaml).

A story's shape (taxonomy §10: join or take away with the result, the change or the start unknown; two parts and a
whole; compare, and which side is unknown; the two-step shapes) is what decides the operation, so it decides the
answer. The engine's own stories carry it by construction (`words.structure_of`, exact); a story written by an educator
or printed on an outside paper does not. Reading a shape from words is judgement, so Jev chooses it from the
taxonomy's own shape cases (ADR 0036) — and everything after is code: the numbers are read from the text, a one-step
answer is the shape's operation on them (the operation is the engine's own templates'), and the skill set and level are
the ones whose level names the case. Code also holds Jev's choice to the story's numbers: a shape whose own stories
print two numbers is not taken for a story that prints four; a one-step question over three numbers is extra
information by definition. A choice Jev is not `story.shape_sure_above` sure of is left for a person, and so is one the
numbers contradict; a number written in words leaves the answer to a person.
"""

import json
import re

from engine.adapters import jev
from engine.assess import words as W
from engine.core import db

PURPOSE = "story_shape"
GOLD = db.REPO_ROOT / "supabase" / "seed" / "story_shape_gold.json"
BAR = ("story.shape_sure_above", 0.6)
EXTRA = "EXTRA_INFORMATION"
NUMBER = re.compile(r"(?<![\w.])\d[\d,]*(?!\w)")  # "Class 2A" is a name, not a number


def _bar(conn):
    row = conn.execute("select value from threshold where key = %s", (BAR[0],)).fetchone()
    return float(row["value"]) if row else BAR[1]


def shapes(conn):
    """{shape: (case code, what it is — the case's label and one of the engine's own stories of that shape)} for every
    taxonomy case that is a story's shape. The case rows alone say "work backwards" or "several conditions" with no
    story to show; a story beside each is what a reader of shapes needs."""
    rows = conn.execute(
        "select code, label, match->>'structure' as shape from taxonomy_case where match ? 'structure' order by code"
    ).fetchall()
    return {
        r["shape"]: (r["code"], f"{r['label']}. Stories of this shape: {_example(r['shape'])}") for r in rows
    }


def _example(shape):
    """Every one of the engine's own stories of the shape, not the first: CONSTRAINT's first reads like working
    backwards, and a reader shown only that one took "two numbers, their total and their difference" for a compare."""
    stories = [t["text"].format(a=45, b=12, c=8, n="Asha", n2="Ravi") for t in W.templates(structure=shape)]
    return " / ".join(stories)


def counts(shape):
    """How many numbers the engine's own stories of this shape print ({2} for a one-step shape, {3} for most of two)."""
    return {len(set(re.findall(r"\{([abc])\}", t["text"]))) for t in W.templates(structure=shape)}


def one_step_op(shape):
    """'+' or '-' for a one-step shape, as the engine's own stories of that shape carry it; None for any other."""
    ops = {t["op"] for t in W.templates("word_1step", structure=shape)}
    return ops.pop() if len(ops) == 1 and ops <= {"+", "-"} else None


def numbers(text):
    return [int(n.replace(",", "")) for n in NUMBER.findall(text)]


def answer(shape, text):
    """The one-step answer, computed: the shape's operation on the story's two numbers (a take-away of the smaller
    from the larger, whichever is written first). None when code cannot be sure of it."""
    op, ns = one_step_op(shape), numbers(text)
    if op is None or len(ns) != 2:
        return None
    return sum(ns) if op == "+" else max(ns) - min(ns)


def placed(conn, case):
    """[(skill set, level)] whose level names this case."""
    return [
        (r["code"], r["level"])
        for r in conn.execute(
            "select s.code, l.key as level from skill_set s, jsonb_each(s.difficulty) l"
            " where l.value->'check'->'cases' ? %s order by s.code, l.key",
            (case,),
        )
    ]


def name(conn, text, ask=None):
    """→ {shape, case, sure, how ('template' | 'jev' | 'jev+code' | None), answer, placed, ranked, why}."""
    known = shapes(conn)
    own = W.structure_of(text)
    if own in known:
        return _named(conn, known, own, text, 1.0, "template", [], "")
    about = {s: meaning for s, (_, meaning) in known.items()}
    try:
        got = (ask or jev.decide)(conn, PURPOSE, {"story": text.strip()}, about)
    except jev.JevError as e:
        return _unnamed(str(e))
    ranked = [(s, round(p, 3)) for s, p in got["ranked"][:3]]
    best, p = got["ranked"][0] if got["ranked"] else (got["choice"], 0.0)
    if p < _bar(conn):
        return _unnamed(
            f"Jev is {p:.2f} sure it is {best}; below {_bar(conn)} a person names the shape", ranked
        )
    n, want = len(numbers(text)), counts(best)
    if n in want:
        return _named(conn, known, best, text, round(p, 3), "jev", ranked, "")
    if one_step_op(best) and n == 3 and EXTRA in known:
        # a one-step question over three numbers: one of them is not needed — which is what the shape is
        why = f"Jev read {best}; the story prints 3 numbers, so one is not needed"
        return _named(conn, known, EXTRA, text, round(p, 3), "jev+code", ranked, why)
    return _unnamed(
        f"Jev read {best}, whose stories print {sorted(want)} numbers; this one prints {n}", ranked
    )


def _named(conn, known, shape, text, sure, how, ranked, why):
    case = known[shape][0]
    return {
        "shape": shape,
        "case": case,
        "sure": sure,
        "how": how,
        "answer": answer(shape, text),
        "placed": placed(conn, case),
        "ranked": ranked,
        "why": why,
    }


def _unnamed(why, ranked=()):
    return {
        "shape": None,
        "case": None,
        "sure": None,
        "how": None,
        "answer": None,
        "placed": [],
        "ranked": list(ranked),
        "why": why,
    }


def gold():
    return json.loads(GOLD.read_text(encoding="utf-8"))["stories"]


def evaluate(conn, stories=None, ask=None):
    """Jev against the gold: of the stories it names, how many shapes are right and how many one-step answers are
    right of those it computes (the number that matters — a wrong shape of the same operation still gives the right
    key); how many it leaves for a person."""
    stories = stories if stories is not None else gold()
    named = right = keyed = wrong_answer = left = 0
    misses = []
    for g in stories:
        got = name(conn, g["text"], ask)
        if got["shape"] is None:
            left += 1
            misses.append({"text": g["text"], "want": g["shape"], "got": None, "why": got["why"]})
            continue
        named += 1
        right += got["shape"] == g["shape"]
        if got["answer"] is not None:  # a key computed for a story that is not one step is a wrong key too
            keyed += 1
            wrong_answer += got["answer"] != g.get("answer")
        if got["shape"] != g["shape"]:
            misses.append({"text": g["text"], "want": g["shape"], "got": got["shape"], "why": ""})
    return {
        "n": len(stories),
        "named": named,
        "right": right,
        "left": left,
        "keyed": keyed,
        "wrong_answer": wrong_answer,
        "misses": misses,
    }
