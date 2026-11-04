"""The K2 class picture and a child's page (task M1-03 part B, goals/m1-03-k2-reads.yaml). Only reading: the child's
state per skill is `child_observed_state`, which the graph rebuilds from confirmed observations (M1-02); nothing here
works a state out.

A child is by Sr. No. (`enrolment.roll_no`) and never by name or id. A cell exists only where the child was seen on
the skill: an empty cell is "not seen", which is not "not secure" (D-008). The state's words and colour are the
`child_state` rows, joined here, never copied. The level shown is the level reached by the child's latest *named*
observation on the skill; "the rest did as expected" names no child, so it shows no level. "Not willing" is an
observation only and appears in no answer. Who may ask: a staff member with a current grant on the class, or one of the
roles in config `k2.reads` on the class's campus.
"""

import datetime as dt
from zoneinfo import ZoneInfo

from engine.core import db
from engine.w3_read import voice_intake, voice_note
from engine.w3_read.voice_store import Refused

CELLS_SQL = """
select s.child_id, e.roll_no, s.skill_code, s.state, cs.words, cs.colour,
       (s.last_seen at time zone %(zone)s)::date as last_seen, lv.reached_level, lv.note_id
from enrolment e
join child_observed_state s on s.child_id = e.child_id and s.grade_code = %(grade)s
join child_state cs on cs.tenant_id = s.tenant_id and cs.code = s.state
left join lateral (
  select o.reached_level, o.note_id
  from evidence_event v join activity_observation o on o.id = v.observation_id
  where v.child_id = s.child_id and v.skill_code = s.skill_code and v.confirmed_by is not null
    and o.entry_mode = 'individual' and o.reached_level is not null
    and not exists (select 1 from activity_observation c where c.supersedes = o.id)
  order by v.observed_at desc, v.id desc limit 1
) lv on true
where e.class_id = %(class)s and e.from_date <= %(day)s and (e.to_date is null or e.to_date >= %(day)s)
  and (%(roll)s::text is null or e.roll_no = %(roll)s)
"""


def cells_params(conn: db.Conn, class_id: str, zone: str, roll: str | None = None) -> dict:
    grade = db.one(conn, "select grade_code from school_class where id = %s", (class_id,))["grade_code"]
    day = dt.datetime.now(ZoneInfo(zone)).date()
    return {"zone": zone, "grade": grade, "class": class_id, "day": day, "roll": roll}


def _allowed(conn: db.Conn, email: str, class_id: str) -> dict:
    """The class (its grade and section, the school's zone) for someone who may see it; refused otherwise."""
    staff = voice_intake.staff_of(conn, email)
    class_id = voice_intake.valid_id(class_id)
    got = conn.execute(
        "select c.grade_code, c.section, coalesce(z.value #>> '{}', 'Asia/Kolkata') as zone,"
        " exists (select 1 from staff_role_grant g join staff s on s.id = g.staff_id"
        "   where g.staff_id = %(staff)s and g.valid_from <= current_date"
        "   and (g.valid_to is null or g.valid_to >= current_date)"
        "   and (g.school_class_id = c.id or (g.school_class_id is null and s.campus_id = c.campus_id"
        "        and g.role_code in (select jsonb_array_elements_text(k.value -> 'coordinator_roles')"
        "                            from config k where k.key = 'k2.reads')))) as ok"
        " from school_class c left join config z on z.key = 'school.time_zone' where c.id = %(class)s",
        {"staff": staff, "class": class_id},
    ).fetchone()
    if got is None:
        raise Refused("Not found.", 404)
    if not got["ok"]:
        raise Refused("This class is not one of yours.", 403)
    return {**got, "class": class_id}


def _today(where: dict) -> dt.date:
    return dt.datetime.now(ZoneInfo(where["zone"])).date()


def _cell(r: dict) -> dict:
    return {
        "state": r["state"], "words": r["words"], "colour": r["colour"],
        "level": r["reached_level"], "last_seen": r["last_seen"].isoformat(),
    }  # fmt: skip


def class_picture(conn: db.Conn, email: str, class_id: str) -> dict:
    """The class's children by Sr. No. against the skills anyone was seen on, a cell where a child was seen."""
    where = _allowed(conn, email, class_id)
    cells = conn.execute(CELLS_SQL, cells_params(conn, where["class"], where["zone"])).fetchall()
    day = _today(where)
    roll = conn.execute(
        "select roll_no from enrolment where class_id = %s and from_date <= %s and (to_date is null or to_date >= %s)",
        (where["class"], day, day),
    ).fetchall()
    seen = sorted({c["skill_code"] for c in cells})
    skills = conn.execute(
        "select code, name from registry_skill where code = any(%s) order by code", (seen,)
    ).fetchall()
    by_roll: dict[str, dict] = {r["roll_no"]: {} for r in roll}
    for c in cells:
        by_roll[c["roll_no"]][c["skill_code"]] = _cell(c)
    children = [
        {"roll_no": n, "cells": by_roll[n]} for n in sorted(by_roll, key=lambda n: (len(n), n))
    ]  # fmt: skip
    return {
        "class": f"{where['grade_code']} {where['section']}",
        "skills": [{"code": s["code"], "name": s["name"]} for s in skills],
        "children": children,
    }


def child_page(conn: db.Conn, email: str, class_id: str, roll_no: str) -> dict:
    """One child's skills, newest first: its name, state, level, last seen and the free sentence of the note it came
    from, when there was one."""
    where = _allowed(conn, email, class_id)
    here = conn.execute(
        "select 1 from enrolment where class_id = %s and roll_no = %s and from_date <= %s"
        " and (to_date is null or to_date >= %s)",
        (where["class"], roll_no, _today(where), _today(where)),
    ).fetchone()
    if here is None:
        raise Refused("There is no such Sr. No. in this class.", 404)
    cells = conn.execute(CELLS_SQL, cells_params(conn, where["class"], where["zone"], roll_no)).fetchall()
    names = {
        r["code"]: r["name"]
        for r in conn.execute(
            "select code, name from registry_skill where code = any(%s)", ([c["skill_code"] for c in cells],)
        ).fetchall()
    }
    words = {
        n["id"]: voice_note.read(n["transcript"] or "").line("sentence")
        for n in conn.execute(
            "select id, transcript from pii.educator_note where id = any(%s)",
            ([c["note_id"] for c in cells if c["note_id"]],),
        ).fetchall()
    }
    cells.sort(key=lambda c: (c["last_seen"], c["skill_code"]), reverse=True)
    skills = []
    for c in cells:
        line = words.get(c["note_id"])
        skills.append({
            "code": c["skill_code"], "name": names.get(c["skill_code"], c["skill_code"]),
            **_cell(c), "sentence": (line.text or line.words) if line else None,
        })  # fmt: skip
    return {"class": f"{where['grade_code']} {where['section']}", "roll_no": roll_no, "skills": skills}
