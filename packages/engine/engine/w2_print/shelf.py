"""What a paper is drawn against (N5): the bank's taught skill sets, each skill set's levels for a child's grade, the
school's rule for how far from its rung and how hard a paper reaches, and how long a home paper is — all rows, read
once a batch (`one_batch`) rather than once a child. `focus_paper` draws and prints against them; split from it when
it passed its 400 lines (2026-10-01).
"""

import contextvars
from contextlib import contextmanager
from typing import Any

from engine.core import roster, settings

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
    return int(settings.config(conn, "assemble.items_per_sheet", 12))


def rule(conn) -> dict:
    """How far from its rung an area may be worked on, the stretch level for each strong state, and where Easy
    ends — all rows."""
    return _once("rule", lambda: _rule(conn))


def _rule(conn) -> dict:
    r = dict(
        settings.config(
            conn, "focus", {"reach": 2, "stretch": {"secure": "Hard", "stretch_ready": "Advance"}}
        )
    )
    r["easy_below"] = settings.threshold(conn, "next_sheet.demote_below", 0.5)
    return r


def catalog(conn, section: str | None = None, every: bool = False) -> list[dict]:
    """The bank's skill sets taught in a class: rung, place on the ladder, the skill each is for, every skill it uses.
    A skill the child's class has not been taught is never on their paper, whatever their map shows
    (`skill_taught_in`: the class's own word on the skill, else the school's — goals/f1f-taught-per-class.yaml,
    goals/t1-topics-are-operations.yaml). Without a class, the school's word. With `every`, every skill set, taught or
    not: what an educator may choose (L7, ADR 0081)."""
    return _once(("catalog", section, every), lambda: _catalog(conn, section, every))


def _catalog(conn, section, every) -> list[dict]:
    rows = conn.execute(
        "select s.code, s.rung_code, r.ladder_order,"
        # its own skill is the one its rung declares first (`rung.skill_codes`): a count of its questions' skills made
        # equal groups, whose every question adds and multiplies, Addition by the alphabet. None while it has no
        # question, so no paper is drawn from a skill set with nothing in it
        " case when exists (select 1 from item i where i.skill_set_code = s.code and i.status = 'active')"
        "   then r.skill_codes[1] end as own,"
        " (select coalesce(array_agg(distinct x), '{}') from item i, unnest(i.skill_codes) x"
        "   where i.skill_set_code = s.code and i.status = 'active') as skills"
        " from skill_set s left join rung r on r.code = s.rung_code and r.tenant_id = s.tenant_id"
        " where %s or skill_taught_in(s.tenant_id, s.code, %s)",
        (every, section),
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


def approved_levels(conn) -> dict:
    """{skill set: the levels whose questions the coordinator has approved} (`skill_set.level_approved`,
    goals/f1d-questions-approved-per-level.yaml): the levels a paper may draw on once F1g ships
    (goals/f1g-approval-gates-papers.yaml)."""
    return {
        r["code"]: set(r["level_approved"] or {})
        for r in conn.execute("select code, level_approved from skill_set")
    }


def closing(conn) -> list[dict]:
    """What F1g would take off papers, measured before it ships: for every class on the roll, each level its papers
    may draw on today — taught in the class, its grade's or below — whose questions are not approved yet, with how
    many questions it holds. Nothing is written."""
    approved = approved_levels(conn)
    held = {
        (r["code"], r["level"]): r["n"]
        for r in conn.execute(
            "select skill_set_code as code, difficulty as level, count(*)::int as n from item"
            " where status = 'active' group by 1, 2"
        )
    }
    out = []
    for c in conn.execute("select distinct section from child where active order by section").fetchall():
        band = roster.class_band(conn, c["section"])
        usable = _levels(conn, band)
        for s in catalog(conn, c["section"]):
            for level in usable.get(s["code"], ()):
                if level not in approved.get(s["code"], set()):
                    q = held.get((s["code"], level), 0)
                    out.append(
                        {
                            "class": c["section"],
                            "grade": band,
                            "skill": s["code"],
                            "level": level,
                            "questions": q,
                        }
                    )
    return out
