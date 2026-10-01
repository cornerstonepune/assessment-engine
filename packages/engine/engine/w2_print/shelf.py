"""What a paper is drawn against (N5): the bank's taught skill sets, each skill set's levels for a child's grade, the
school's rule for how far from its rung and how hard a paper reaches, and how long a home paper is — all rows, read
once a batch (`one_batch`) rather than once a child. `focus_paper` draws and prints against them; split from it when
it passed its 400 lines (2026-10-01).
"""

import contextvars
from contextlib import contextmanager
from typing import Any

from engine.w2_print.assemble import _config, _threshold

_BATCH: contextvars.ContextVar[dict[str, Any] | None] = contextvars.ContextVar(
    "focus_paper_batch", default=None
)


@contextmanager
def one_batch():
    """Within a batch of papers the catalogue, the levels, the rule and the names are read once, not once a child:
    planning a class read them again for every child (code review, 2026-09-30)."""
    token = _BATCH.set({})
    try:
        yield
    finally:
        _BATCH.reset(token)


def _once(key, read):
    memo = _BATCH.get()
    if memo is None:
        return read()
    if key not in memo:
        memo[key] = read()
    return memo[key]


def home_length(conn) -> int:
    """How many questions a home paper holds: the `assemble.items_per_sheet` row."""
    return int(_config(conn, "assemble.items_per_sheet", 12))


def rule(conn) -> dict:
    """How far from its rung an area may be worked on, the stretch level for each strong state, and where Easy
    ends — all rows."""
    return _once("rule", lambda: _rule(conn))


def _rule(conn) -> dict:
    r = dict(_config(conn, "focus", {"reach": 2, "stretch": {"secure": "Hard", "stretch_ready": "Advance"}}))
    r["easy_below"] = _threshold(conn, "next_sheet.demote_below", 0.5)
    return r


def catalog(conn) -> list[dict]:
    """The bank's taught skill sets: rung, place on the ladder, the skill each is for, every skill it uses. A skill
    the school does not teach yet is never on a child's paper, whatever the child's map shows."""
    return _once("catalog", lambda: _catalog(conn))


def _catalog(conn) -> list[dict]:
    rows = conn.execute(
        "select s.code, s.rung_code, r.ladder_order,"
        " (select x from item i, unnest(i.skill_codes) x where i.skill_set_code = s.code"
        "   and i.status = 'active' group by x order by count(*) desc, x limit 1) as own,"
        " (select coalesce(array_agg(distinct x), '{}') from item i, unnest(i.skill_codes) x"
        "   where i.skill_set_code = s.code and i.status = 'active') as skills"
        " from skill_set s left join rung r on r.code = s.rung_code and r.tenant_id = s.tenant_id"
        " where exists (select 1 from topic t where t.tenant_id = s.tenant_id and t.code = s.topic_code and t.taught)"
    ).fetchall()
    return [
        {
            "code": r["code"],
            "rung": r["rung_code"],
            "order": r["ladder_order"],
            "own": r["own"],
            "skills": set(r["skills"]),
        }
        for r in rows
    ]


def _grade(band) -> int:
    """A band's place among the grades: G1 → 1; reasoning's "G2+" → 2."""
    digits = "".join(ch for ch in str(band or "") if ch.isdigit())
    return int(digits) if digits else 0


def _levels(conn, band=None) -> dict:
    """{skill set: its levels}. With a child's band, only the levels of that child's grade or below: each level
    belongs to one grade (`skill_set.level_band`, else the skill's own), and a child is never given a level of a
    grade above their own — a Grade 1 child meets 2-digit + 1-digit only at the levels Grade 1 teaches."""
    return _once(("levels", band), lambda: _read_levels(conn, band))


def _read_levels(conn, band) -> dict:
    out = {}
    for r in conn.execute(
        "select s.code, s.difficulty, s.level_band, r.band from skill_set s"
        " left join rung r on r.tenant_id = s.tenant_id and r.code = s.rung_code"
    ):
        defined = tuple(r["difficulty"] or {})
        if band is not None:
            defined = tuple(
                d for d in defined if _grade((r["level_band"] or {}).get(d) or r["band"]) <= _grade(band)
            )
        out[r["code"]] = defined
    return out
