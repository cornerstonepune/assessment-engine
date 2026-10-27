"""Questions made from an educator's sample (goals/gen_from_a_sample.yaml). Nimish, 2026-10-26: "The capability to edit a
certain level in a skill by putting in the sample questions, and the ability for the system to then generate a certain
number of questions of that pattern."

English: the prompt row `english_generate` (rule 2) writes them, and every one is checked by code exactly as an
educator's own sample is (`english_edit.check`, #323) before it is stored; one that fails, or repeats a question already
there, is never shown or stored, and the educator is told how many and why. Maths: questions are made by code (ADR 0005):
the sample is measured by code (`assess/tags`), and where it is a case its level's generator holds, code makes more of
that case (`refill.fill_cases`); where it is not, the sample is kept as a sample only and nothing is made. A model's
number is never the last word. Whatever is made is a draft: it names its sample, and its level waits for approval.
"""

import json
import re
from collections import Counter
from typing import Any

from engine.adapters import llm
from engine.assess import items as I
from engine.assess import tags
from engine.core import db, settings
from engine.w1_bank import cases, english_edit, english_words, refill

PURPOSE = "english_generate"
SAMPLE = re.compile(r"^\s*(\d{1,4})\s*([+\-−×x*÷/])\s*(\d{1,4})\s*(=\s*\??\s*)?$")
OPS = {"+": "+", "-": "-", "−": "-", "×": "×", "x": "×", "*": "×", "÷": "÷", "/": "÷"}
FMT = {"line": "bare_sum", "columns": "column_grid"}
CARRIED = (
    "passage_code",
    "rubric_code",
)  # a question of the sample's pattern is about its passage, read by its rubric
NOT_IN_FORM = "The writer's reply was not in the form we need; nothing was added."


def most(conn: db.Conn) -> int:
    """The most questions asked for at once (a row)."""
    return int(settings.threshold(conn, "generate.max_per_request", 20))


def _too_many(conn: db.Conn, n: int) -> str:
    m = most(conn)
    return "" if 1 <= n <= m else f"Ask for at least 1 question and at most {m}."


def _key(s: dict[str, Any]) -> str:
    return english_words.plain(f"{s.get('text') or ''} {s.get('ask') or ''}")


def _variables(conn: db.Conn, code: str, level: str, kind: str, s: dict, here: list[dict], n: int) -> dict:
    row = db.one(
        conn,
        "select k.name, k.learning_objective, l.looks_like, l.rule, q.words,"
        " coalesce((select jsonb_object_agg(m.code, m.name) from skill_mistake x join misconception m"
        "   on m.tenant_id = x.tenant_id and m.code = x.misconception_code and m.op = x.op"
        "   where x.skill_code = k.code), '{}'::jsonb) as mistakes,"
        " (select p.text from passage p where p.code = %s) as passage"
        " from skill k join skill_level l on l.tenant_id = k.tenant_id and l.skill_code = k.code and l.difficulty = %s"
        " join question_type q on q.tenant_id = k.tenant_id and q.code = %s where k.code = %s",
        (s["passage_code"], level, kind, code),
    )
    return {
        "n": str(n),
        "skill": f"{row['name']}: {row['learning_objective']}",
        "level": f"{level}: {row['looks_like'] or ''}",
        "rule": row["rule"],
        "kind": row["words"],
        "passage": f"Every question is about this passage:\n{row['passage']}" if row["passage"] else "",
        # the passage and the rubric are the sample's, carried over by code (`_written`): the writer is not asked
        "sample": {k: s[k] for k in (*english_edit.COLUMNS, "wrong") if k not in CARRIED},
        "mistakes": row["mistakes"],
        "already": [h["text"] or h["ask"] for h in here],
    }


def english(conn: db.Conn, code: str, level: str, kind: str, ord: int, n: int, by: str) -> dict[str, Any]:
    """`n` questions like English sample `ord`, written by the model and each checked by code. {made, why, returned,
    kept, thrown: [{why, n}], ords}: `made` is false, with nothing stored, when it is refused or the model fails."""

    def refuse(why: str) -> dict[str, Any]:
        return {"made": False, "why": why, "returned": 0, "kept": 0, "thrown": [], "ords": []}

    if not by.strip():
        return refuse("Say who asks for them.")
    if not english_edit.is_english(conn, code):
        return refuse(
            "This skill's questions are made by code from each level's rule: type a sum under its level instead."
        )
    if why := _too_many(conn, n):
        return refuse(why)
    s = english_edit.current(conn, code, level, kind, ord)
    if not s:
        return refuse("That sample is not on this level any more.")
    meta: dict[str, Any] = {}
    try:
        returned, kept, thrown = _written(conn, code, level, kind, s, n, meta)
    except llm.LLMSchemaError:
        return refuse(NOT_IN_FORM)
    except llm.LLMError as e:
        if "an active prompt" in str(e):  # llm.active_prompt's refusal: no version of it is active yet
            return refuse(
                "Making questions is not switched on yet: its prompt is scored first (engine eval english_generate)."
            )
        return refuse(f"The questions could not be made just now ({e}). Nothing was stored.")
    ords = english_edit.made(conn, code, level, kind, ord, kept, by, meta.get("flow_run_id"))
    return {"made": True, "why": "", "returned": returned, "kept": len(kept), "thrown": thrown, "ords": ords}


def _written(
    conn: db.Conn, code: str, level: str, kind: str, s: dict, n: int, meta: dict, version: int | None = None
) -> tuple[int, list[dict], list[dict]]:
    """The model's questions like `s`, each checked by code, nothing stored: (how many it returned, the first `n` that
    passed, [{why, n}] for the rest). A question repeating one already here, or another it wrote, is thrown away."""
    here = conn.execute(
        "select text, ask from english_sample_now where skill_code = %s and difficulty = %s and question_type = %s",
        (code, level, kind),
    ).fetchall()
    out = llm.generate(
        conn, PURPOSE, _variables(conn, code, level, kind, s, here, n), meta=meta, version=version
    )
    seen = {_key(h) for h in here}
    kept, thrown = [], Counter()
    for q in out["questions"]:
        q = {**q, **{k: s[k] for k in CARRIED}}
        faults = english_edit.check(conn, code, level, kind, q)
        if _key(q) in seen:
            faults = {"text": ["It is the same as a question already here."]} | faults
        if faults or len(kept) >= n:
            thrown[next(iter(faults.values()))[0] if faults else "More than were asked for."] += 1
            continue
        seen.add(_key(q))
        kept.append(q)
    return len(out["questions"]), kept, [{"why": w, "n": c} for w, c in thrown.most_common()]


def evaluate(conn: db.Conn, version: int | None = None) -> dict[str, Any]:
    """`engine eval english_generate`: on the fixed set (supabase/seed/english_generate_gold.json), the share of the
    questions returned that pass every check, and why the rest failed; a reply out of form counts as the questions
    asked for, none kept. Nothing is stored; the runs are (`flow_run`)."""
    gold = json.loads((db.REPO_ROOT / "supabase" / "seed" / "english_generate_gold.json").read_text())
    returned = kept = 0
    why: Counter = Counter()
    for g in gold["samples"]:
        s = english_edit.current(conn, g["skill"], g["level"], g["kind"], g["ord"])
        if s is None:
            raise LookupError(
                f"the eval's sample {g} is not in the seed any more: change the set with a new score"
            )
        try:
            r, k, t = _written(conn, g["skill"], g["level"], g["kind"], s, gold["n"], {}, version)
        except llm.LLMSchemaError:  # a reply out of form keeps none of the questions asked for
            r, k, t = gold["n"], [], [{"why": NOT_IN_FORM, "n": gold["n"]}]
        returned, kept = returned + r, kept + len(k)
        why.update({x["why"]: x["n"] for x in t})
    return {"returned": returned, "kept": kept, "thrown": dict(why.most_common())}


def _measured(conn: db.Conn, code: str, text: str, layout: str) -> list[str] | None:
    """Every taxonomy case a typed sum is, as code measures it; None when it is not a sum code can read."""
    m = SAMPLE.match(text)
    if not m or layout not in FMT:
        return None
    a, op, b = int(m[1]), OPS[m[2]], int(m[3])
    rung = db.one(conn, "select rung_code from skill where code = %s", (code,))["rung_code"]
    spec = {"a": a, "b": b, "op": op, "layout": "column" if layout == "columns" else "line"}
    it = I.Item(item_id="", template="", rung=rung or "", skills=[], signal="", fmt=FMT[layout], scaffolded=False,
                stem="", spec=spec, responses=[])  # fmt: skip
    return cases.of(FMT[layout], tags.derive(it), cases.matches(conn))


def maths(conn: db.Conn, code: str, level: str, text: str, layout: str, n: int, by: str) -> dict[str, Any]:
    """`n` questions like a typed Maths sample ("47 + 38", in a line or in columns), made by code. {made, why, cases,
    kept, sample}: the sample is kept (`maths_sample`) whenever it is a sum code can read, made into questions only when
    it is a case its level's generator holds."""

    def refuse(why: str, found: list[str] | None = None, sample: str | None = None) -> dict[str, Any]:
        return {"made": False, "why": why, "cases": found or [], "kept": 0, "sample": sample}

    if not by.strip():
        return refuse("Say who asks for them.")
    if english_edit.is_english(conn, code):
        return refuse("An English skill's questions are made from one of its samples.")
    if why := _too_many(conn, n):
        return refuse(why)
    level_row = conn.execute(
        "select tenant_id, rule from skill_level where skill_code = %s and difficulty = %s", (code, level)
    ).fetchone()
    if not level_row:
        return refuse("This skill has no such level.")
    found = _measured(conn, code, text, layout)
    if found is None:
        return refuse("Write the sample as a sum with two numbers, like 47 + 38 or 52 − 19.")
    on = sorted(set(found) & set((level_row["rule"].get("check") or {}).get("cases", [])))[:1]
    made = (
        [it.item_id for it in refill.fill_cases(conn, code, level, 0, quotas={c: n for c in on})[2]]
        if on
        else []
    )
    sample = str(
        db.one(
            conn,
            "insert into maths_sample (tenant_id, skill_code, difficulty, text, layout, cases, item_ids, given_by)"
            " values (%s, %s, %s, %s, %s, %s, array(select id from item where item_key = any(%s)), %s) returning id",
            (level_row["tenant_id"], code, level, text.strip(), layout, on, made, by),
        )["id"]
    )
    if not on:
        return refuse(
            f"Your sample is kept as a sample. It is not a kind of sum {level} makes, so no question was made from it.",
            sample=sample,
        )
    if not made:
        return refuse("Every sum of this kind is already in the bank, so none was made.", on, sample)
    english_edit.withdraw(conn, code, level)
    return {"made": True, "why": "", "cases": on, "kept": len(made), "sample": sample}
