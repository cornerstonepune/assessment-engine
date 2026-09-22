"""The skills a question uses, read from the question itself (ADR 0023, step 8a). Deterministic, no I/O.

A question uses the skill of every operation it asks for and its kind's own skills — a missing number is
also a missing-number equation, a story also a word problem — plus money when its sentence is about
money. Which operation maps to which skill, and which kind carries which skills, are rows
(`config: skills.*`), handed in as `rules`; this module only reads the question.

The rung's own skills decide the order and nothing else: the ones the question uses come first, in the
rung's order, so `skill_codes[1]` stays the question's own skill for every reader that takes the first.
"""

import re

from . import words as W

MINUS = ("−", "-")


def _sign(op):
    return "-" if op in MINUS else op


def operations(fmt, spec, stem=""):
    """The operations a child carries out on this question, in the order the question asks for them."""
    if "budget" in spec:
        return ["+", "-"]  # the costs are added up, and the total is taken from the budget
    if spec.get("ops"):
        return [_sign(o) for o in spec["ops"]]
    if fmt == "word_2step":
        tpl = W.template_of(stem)  # the operations are the story template's own (`word_templates.json`)
        return [o for o in dict.fromkeys(tpl["op"])] if tpl else ["-"]
    if spec.get("addends") or fmt == "number_wall":
        return ["+"]
    if fmt == "balance_scale":
        return ["+", "-"]  # one side added up, the known part taken from it
    if fmt == "explain_claim":
        return ["+"] if spec.get("topic") == "compensation" else []
    if spec.get("op"):
        return [_sign(spec["op"])]
    text = spec.get("text") or ""
    m = re.search(r"\d\s*([+−\-×])\s*[\d□]|□\s*([+−\-×])", text)
    return [_sign(m.group(1) or m.group(2))] if m else []


def used(fmt, spec, stem, rung_skills, rules):
    """Every registry skill the question uses, the rung's own first."""
    found = list(rules["by_kind"].get(fmt, []))
    found += [skill for symbol, skill in rules["by_symbol"].items() if symbol in (stem or "")]
    found += [rules["by_operation"][op] for op in operations(fmt, spec, stem) if op in rules["by_operation"]]
    found = list(dict.fromkeys(found))
    lead = [s for s in rung_skills if s in found]
    return lead + [s for s in found if s not in lead]


def charges(fmt, spec, stem, skills_used, codes, vocab, rules):
    """{mistake: skill} — the skill a wrong answer showing each mistake counts against (ADR 0023).

    In order: this kind's own table (`skills.charges_by_kind`, approved once by a person), then the
    mistake's vocabulary row, then the question's operation when it has exactly one. A mistake that
    would charge a skill the question does not use — or that nothing names — charges the question's
    own skill, so a wrong answer never lands on a skill the question never asked for.
    """
    ops = operations(fmt, spec, stem)
    own = skills_used[0] if skills_used else None
    table = rules.get("charges_by_kind", {}).get(fmt, {})
    out = {}
    for code in codes:
        skill = table.get(code)
        if skill is None:
            skill_from, row_skill = (
                vocab.get((code, ops[0]) if len(ops) == 1 else None)
                or vocab.get((code, "any"))
                or (None, None)
            )
            if skill_from == "row":
                skill = row_skill
            elif len(ops) == 1:
                skill = rules["by_operation"].get(ops[0])
        out[code] = skill if skill in skills_used else own
    return out
