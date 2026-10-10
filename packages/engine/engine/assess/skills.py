"""The skills a question uses, read from the question itself (ADR 0023, step 8a). Deterministic, no I/O.

A question uses the skill of every operation it asks for and its kind's own skills — a missing number is
also a missing-number equation, a story also a word problem — plus money when its sentence is about
money. Which operation maps to which skill, and which kind carries which skills, are rows
(`config: skills.*`), handed in as `rules`; this module only reads the question.

The rung's own skills decide the order and nothing else: the ones the question uses come first, in the
rung's order, so `skill_codes[1]` stays the question's own skill for every reader that takes the first.

A written method that adds its steps — partitioning, a grid, expanded columns, a lattice, long multiplication's rows —
uses addition too (`skills.by_method`, assumption A11), so a slip adding them counts against addition (ADR 0055).
"""

import re
from typing import Any

from . import md_tags as MD
from . import operations as O
from . import words as W


def _sign(op: str) -> str:
    return O.sign(op) or op


def operations(fmt: str, spec: dict[str, Any], stem: str | None = "") -> list[str]:
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
    m = re.search(r"\d\s*([+−\-×÷])\s*[\d□]|□\s*([+−\-×÷])", text)  # as printed: a / may be a fraction
    return [_sign(m.group(1) or m.group(2))] if m else []


def method(fmt: str, spec: dict[str, Any]) -> str | None:
    """The written method a question is worked in: its own, or a straight calculation's (`md_tags.standard_method`)."""
    if spec.get("method") or not {"a", "b", "op"} <= spec.keys() or _sign(spec["op"]) not in ("×", "÷"):
        return spec.get("method")
    layout = spec.get("layout") or ("column" if fmt == "column_grid" else "horizontal")
    return MD.standard_method(_sign(spec["op"]), spec["a"], spec["b"], layout)


def kind_skills(rules: dict[str, Any], fmt: str, ops: list[str]) -> list[str]:
    """A kind's own skills (`skills.by_kind`): one list, or a list for each operation the question carries out. Equal
    groups that multiply are Grade 1's groups added again and use addition too; equal groups that divide do not."""
    own: list[str] | dict[str, list[str]] = rules["by_kind"].get(fmt, [])
    return list(own) if isinstance(own, list) else [skill for op in ops for skill in own.get(op, [])]


def used(
    fmt: str, spec: dict[str, Any], stem: str | None, rung_skills: list[str], rules: dict[str, Any]
) -> list[str]:
    """Every registry skill the question uses, the rung's own first."""
    ops = operations(fmt, spec, stem)
    found = kind_skills(rules, fmt, ops)
    found += [skill for symbol, skill in rules["by_symbol"].items() if symbol in (stem or "")]
    found += [rules["by_operation"][op] for op in ops if op in rules["by_operation"]]
    found += rules["by_method"].get(method(fmt, spec) or "", [])
    found = list(dict.fromkeys(found))
    lead = [s for s in rung_skills if s in found]
    return lead + [s for s in found if s not in lead]


def charges(
    fmt: str,
    spec: dict[str, Any],
    stem: str | None,
    skills_used: list[str],
    codes: list[str],
    vocab: dict[tuple[str, str], tuple[str | None, str | None]],
    rules: dict[str, Any],
) -> dict[str, str | None]:
    """{mistake: skill} — the skill a wrong answer showing each mistake counts against (ADR 0023).

    In order: this kind's own table (`skills.charges_by_kind`, approved once by a person), then the
    mistake's vocabulary row, then the question's operation when it has exactly one. A mistake with no row for the
    question's one operation and a row for exactly one other the question also carries out is that one's — the steps
    of a multiplication added without a carry are addition's (`M_NOCARRY`, assumption A11), and a slip taking away
    inside a long division subtraction's (`M_FACT_PM1`, whose + row the division never uses). A mistake that
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
            # the operations the mistake has a row for that the question uses: a take-away slip inside a long
            # division has a row for + and one for −, and only − is carried out there
            theirs = [
                op
                for c, op in vocab
                if c == code and op in rules["by_operation"] and rules["by_operation"][op] in skills_used
            ]
            # a mistake of another operation the question carries out inside its own: a multiplication's steps added
            # without a carry are addition's (A11), a long division's take-away slips subtraction's; every other
            # mistake reads as it always has
            inside = len(ops) == 1 and (code, ops[0]) not in vocab and len(theirs) == 1
            at = theirs if inside else ops
            skill_from, row_skill = (
                (vocab.get((code, at[0])) if len(at) == 1 else None)
                or vocab.get((code, "any"))
                or (None, None)
            )
            if skill_from == "row":
                skill = row_skill
            elif len(at) == 1:
                skill = rules["by_operation"].get(at[0])
        out[code] = skill if skill in skills_used else own
    return out
