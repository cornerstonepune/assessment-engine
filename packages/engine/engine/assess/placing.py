"""Where a question belongs among the calculation skills (ADR 0034). Pure: no database.

A calculation skill is one operation and one digit shape (`check.within`); its levels are taxonomy cases on
those numbers. A question belongs to the one skill whose shape it has, at the hardest of Easy · Medium · Hard
it is a case of when it is a straight calculation, or at Advance when it is any other kind. The bank's
questions (`engine bank rehome`) and an old paper's questions (W3, `legacy`) are placed by the same rule.
"""

from engine.assess import taxonomy, verify

CALCULATION = ("bare_sum", "column_grid")
STRAIGHT = ("Hard", "Medium", "Easy")  # hardest first: a carry onto a zero is Hard even if it is one carry


def shaped(skills):
    """The skills that have a shape: rows with `difficulty` whose levels say `within`."""
    return [s for s in skills if any("within" in lv.get("check", {}) for lv in s["difficulty"].values())]


def shape(skill):
    return next(
        lv["check"]["within"] for lv in skill["difficulty"].values() if "within" in lv.get("check", {})
    )


def place(fmt, tags, skills, case_matches):
    """(skill, level) for one question, or None. Raises when two skills' shapes both hold it — a map defect."""
    home = [s for s in shaped(skills) if taxonomy.matches(shape(s), fmt, tags)]
    if len(home) > 1:
        raise ValueError(f"two skills hold the same question: {', '.join(s['code'] for s in home)}")
    if not home:
        return None
    s = home[0]
    for level in (*(STRAIGHT if fmt in CALCULATION else ()), "Advance"):
        check = s["difficulty"].get(level, {}).get("check")
        if check and not verify.dimension_problems(tags, check, fmt, case_matches):
            return s, level
    return None
