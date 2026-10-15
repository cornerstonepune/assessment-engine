"""SF2, measured on a copy of live before the goal is written: what "a format" is, and what each starting rule closes.

A format (ADR 0077, decision 3): the printed format where the template is only the level's numbers written as a name
(ADD.2D2D.REG1, MUL.3D1D, ADD.MULTI3), else the template itself (EQ.TRUE_FALSE, MULT.NTH, SEQ.ON).
Nothing is written.
"""

import re
from collections import defaultdict

from engine.core import db
from engine.w2_print import shelf

NUMBERS = re.compile(r"^(ADD|SUB|MUL|DIV)\.(\dD\dD(\.REG\w*)?|MULTI\d*)$")


def fmt_of(r):
    return r["fmt"] if NUMBERS.match(r["template"] or "") else r["template"]


with db.connect() as c:
    levels = c.execute(
        "select s.code, d.key as level, s.level_approved ? d.key as ok from skill_set s, jsonb_each(s.difficulty) d"
    ).fetchall()
    ok = {(r["code"], r["level"]): r["ok"] for r in levels}
    rows = c.execute(
        "select skill_set_code as s, difficulty as l, template, fmt, count(*)::int as n from item"
        " where status = 'active' and source = 'generated' group by 1, 2, 3, 4"
    ).fetchall()
    closing = shelf.closing(c)
    on_paper = {
        (r["code"], r["level"])
        for r in c.execute(
            "select distinct t.skill_set_code as code, t.difficulty as level from sheet_template t"
            " where t.source = 'library' and t.retired_at is null"
        )
    }

uses = defaultdict(set)  # format -> {(skill, level)}
qs = defaultdict(int)
for r in rows:
    f = fmt_of(r)
    uses[f].add((r["s"], r["l"]))
    qs[f] += r["n"]
print(
    f"formats {len(uses)} · skill x format {len({(s, f) for f, u in uses.items() for s, _ in u})}"
    f" · levels {len({(s, lv) for u in uses.values() for s, lv in u})} · approved levels {sum(ok.values())}"
)

every = {f for f, u in uses.items() if all(ok.get(x) for x in u)}
some = {f for f, u in uses.items() if any(ok.get(x) for x in u)} - every
none = set(uses) - every - some
print(f"formats whose every level is approved {len(every)} · some {len(some)} · none {len(none)}")

shut = {(r["skill"], r["level"]) for r in closing}
print(f"unapproved levels a class's paper may draw today: {len(shut)}")
for name, start in (("every level approved", every), ("any level approved", every | some)):
    waiting = set(uses) - start
    closed_levels = {x for f in waiting for x in uses[f]}
    closed_ok = {x for x in closed_levels if ok.get(x)}
    reach = closed_levels & (shut | {x for x in on_paper if ok.get(x)})
    print(
        f"start approved where {name}: {len(start)} approved, {len(waiting)} waiting"
        f" · levels holding a waiting format {len(closed_levels)} (approved ones among them {len(closed_ok)})"
        f" · of them on a paper today {len(reach)} · questions waiting {sum(qs[f] for f in waiting)}"
    )
    still = {x for x in shut if any(x in uses[f] for f in waiting)}
    print(f"  unapproved levels still drawing an approved format: {len(shut - still)} of {len(shut)}")
print("formats some of whose levels are approved, others not:")
for f in sorted(some, key=lambda f: -len(uses[f])):
    u = uses[f]
    print(f"  {f:<28} levels {len(u)}, approved {sum(1 for x in u if ok.get(x))}, questions {qs[f]}")
