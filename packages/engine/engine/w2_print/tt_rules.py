"""The timetable's rules as rows a person edits (task M1-14 part a; D-072, D-074, D-075). Four kinds, one door:
  period  the times and name of a period of the class's grade (the existing `period` row);
  block   a day, or a weekday of a week, or one period of either, on which nothing may be placed;
  limit   the fewest and most periods of a subject in a week or a fortnight;
  fixed   a `timetable_slot` of kind `fixed`: the school pinned this period, this weekday, this week.
Every change is checked here, written, and recorded in `timetable_rule_edit` with who made it and the row before and
after (append-only). Nothing here places a lesson or runs the generator: that is part b. No model, no name."""

import datetime as dt
import json
from dataclasses import dataclass
from typing import Any

import psycopg

from engine.core import db


class Refused(Exception):
    def __init__(self, words: str, status: int = 422):
        super().__init__(words)
        self.status = status


@dataclass
class Change:
    rule: str
    action: str
    id: str | None = None
    period_id: str | None = None
    starts_at: dt.time | None = None
    ends_at: dt.time | None = None
    label: str | None = None
    on_date: dt.date | None = None
    weekday: int | None = None
    week_code: str | None = None
    reason: str | None = None
    subject_code: str | None = None
    span: str | None = None
    fewest: int | None = None
    most: int | None = None
    text: str | None = None


def _hm(t: dt.time | None) -> str | None:
    return t.strftime("%H:%M") if t else None


def _json(row: dict | None, drop: tuple[str, ...] = ("tenant_id", "created_at", "updated_at")) -> dict | None:
    """A row as the history keeps it: plain text and numbers, ids as text."""
    if row is None:
        return None
    return {
        k: (str(v) if not isinstance(v, int | str | type(None)) else v)
        for k, v in row.items()
        if k not in drop
    }


def classes(conn: db.Conn) -> list[dict]:
    """The classes that have a timetable at all (a class with timetable rows), grade then section."""
    return conn.execute(
        "select c.id::text as id, c.grade_code as grade, c.section from school_class c"
        " where exists (select 1 from timetable_slot s where s.school_class_id = c.id) order by c.grade_code, c.section"
    ).fetchall()


def klass(conn: db.Conn, class_id: str | None, found: list[dict] | None = None) -> dict:
    found = classes(conn) if found is None else found
    if not found:
        raise Refused("No class has a timetable yet.", 404)
    if class_id is None:
        return found[0]
    one = next((c for c in found if c["id"] == str(class_id)), None)
    if one is None:
        raise Refused("That class has no timetable.", 404)
    return one


def _periods(conn: db.Conn, grade: str) -> list[dict]:
    return [
        {"id": r["id"], "ord": r["ord"], "label": r["label"], "starts_at": _hm(r["starts_at"]), "ends_at": _hm(r["ends_at"]), "fixed": r["fixed"]}
        for r in conn.execute(
            "select id::text as id, ord, label, starts_at, ends_at, fixed from period where grade_code = %s order by starts_at",
            (grade,),
        ).fetchall()
    ]  # fmt: skip


def _fixed(conn: db.Conn, class_id: str) -> list[dict]:
    return [
        {"id": r["id"], "period_id": r["period_id"], "label": r["label"], "weekday": r["weekday"], "week": r["week_code"], "text": r["text"]}
        for r in conn.execute(
            "select s.id::text as id, s.period_id::text as period_id, p.label, s.weekday, s.week_code, s.text"
            " from timetable_slot s join period p on p.id = s.period_id"
            " where s.school_class_id = %s and s.kind = 'fixed' and s.valid_to is null"
            " order by s.week_code, s.weekday, p.starts_at",
            (class_id,),
        ).fetchall()
    ]  # fmt: skip


def _subjects(conn: db.Conn, class_id: str) -> tuple[list[dict], dict]:
    """The subjects the class has periods for, and how many sit in week A and week B now."""
    placed: dict[str, dict[str, int]] = {}
    for r in conn.execute(
        "select subject_code, week_code, count(*) as n from timetable_slot where school_class_id = %s"
        " and valid_to is null and kind in ('subject', 'specialist') and subject_code is not null"
        " group by subject_code, week_code",
        (class_id,),
    ).fetchall():
        placed.setdefault(r["subject_code"], {"A": 0, "B": 0})[r["week_code"]] = r["n"]
    return [{"code": c, "name": c.replace("_", " ").capitalize()} for c in sorted(placed)], placed


def _blocks(conn: db.Conn, class_id: str) -> list[dict]:
    return [
        {"id": r["id"], "on_date": r["on_date"].isoformat() if r["on_date"] else None, "weekday": r["weekday"], "week": r["week_code"],
         "period_id": r["period_id"], "period": r["label"], "reason": r["reason"]}
        for r in conn.execute(
            "select b.id::text as id, b.on_date, b.weekday, b.week_code, b.period_id::text as period_id, p.label, b.reason"
            " from timetable_block b left join period p on p.id = b.period_id where b.school_class_id = %s"
            " order by b.on_date nulls last, b.weekday, b.week_code nulls first, p.starts_at nulls first",
            (class_id,),
        ).fetchall()
    ]  # fmt: skip


def _limits(conn: db.Conn, class_id: str) -> list[dict]:
    return [
        dict(r)
        for r in conn.execute(
            "select id::text as id, subject_code, span, fewest, most from timetable_limit where school_class_id = %s"
            " order by subject_code, span",
            (class_id,),
        ).fetchall()
    ]


def _history(conn: db.Conn, class_id: str, me: Any, limit: int = 30) -> list[dict]:
    """The last changes. Who made one is the staff row kept with it; a name is never read (it stays in pii), so the
    page says "You" for the asker's own and "A colleague" for anyone else's."""
    return [
        {"id": r["id"], "rule": r["rule"], "action": r["action"], "who": "You" if r["who"] == me else "A colleague", "at": r["at"].isoformat(), "before": r["before"], "after": r["after"]}
        for r in conn.execute(
            "select id::text as id, rule, action, who, at, before, after from timetable_rule_edit"
            " where school_class_id = %s order by at desc, id limit %s",
            (class_id, limit),
        ).fetchall()
    ]  # fmt: skip


def read(conn: db.Conn, class_id: str | None, me: Any = None) -> dict:
    every = classes(conn)
    k = klass(conn, class_id, every)
    subjects, placed = _subjects(conn, k["id"])
    return {
        "classes": every, "class": k, "periods": _periods(conn, k["grade"]), "fixed": _fixed(conn, k["id"]),
        "blocks": _blocks(conn, k["id"]), "limits": _limits(conn, k["id"]), "subjects": subjects, "placed": placed,
        "history": _history(conn, k["id"], me),
    }  # fmt: skip


def _kept(
    conn: db.Conn, k: dict, staff: Any, rule: str, action: str, before: dict | None, after: dict | None
) -> None:
    conn.execute(
        "insert into timetable_rule_edit (tenant_id, school_class_id, rule, action, who, before, after)"
        " select tenant_id, id, %s, %s, %s, %s::jsonb, %s::jsonb from school_class where id = %s",
        (rule, action, staff, json.dumps(before) if before is not None else None, json.dumps(after) if after is not None else None, k["id"]),
    )  # fmt: skip


def _own_period(conn: db.Conn, k: dict, period_id: str | None) -> dict:
    row = conn.execute(
        "select id::text as id, label, starts_at, ends_at, ord from period where id::text = %s and grade_code = %s",
        (period_id, k["grade"]),
    ).fetchone() if period_id else None  # fmt: skip
    if row is None:
        raise Refused("That period is not one of this class's periods.")
    return row


def _shown(r: dict) -> dict:
    return {
        "id": r["id"],
        "label": r["label"],
        "starts_at": _hm(r["starts_at"]),
        "ends_at": _hm(r["ends_at"]),
    }


def _period(conn: db.Conn, k: dict, c: Change) -> tuple[dict | None, dict | None]:
    if c.action != "set":
        raise Refused("A period is changed, not removed.")
    old = _own_period(conn, k, c.id)
    label = (c.label or "").strip()
    if not label or c.starts_at is None:
        raise Refused("A period needs a name and a start.")
    if c.ends_at is not None and c.ends_at <= c.starts_at:
        raise Refused("A period must end after it starts.")
    for other in conn.execute(
        "select label, starts_at, ends_at from period where grade_code = %s and id::text <> %s",
        (k["grade"], c.id),
    ).fetchall():
        end = other["ends_at"] or other["starts_at"]
        if c.starts_at == other["starts_at"] or (
            c.starts_at < end and other["starts_at"] < (c.ends_at or c.starts_at)
        ):
            raise Refused(f"Those times overlap {other['label']} ({_hm(other['starts_at'])}-{_hm(end)}).")
    conn.execute(
        "update period set label = %s, starts_at = %s, ends_at = %s where id::text = %s",
        (label, c.starts_at, c.ends_at, c.id),
    )
    return _shown(old), _shown({"id": c.id, "label": label, "starts_at": c.starts_at, "ends_at": c.ends_at})


def _block(conn: db.Conn, k: dict, c: Change) -> tuple[dict | None, dict | None]:
    cols = "id::text as id, on_date, weekday, week_code, period_id::text as period_id, reason"
    if c.action == "remove":
        old = conn.execute(
            f"select {cols} from timetable_block where id::text = %s and school_class_id = %s",
            (c.id, k["id"]),
        ).fetchone()  # noqa: S608
        if old is None:
            raise Refused("That block is not there.", 404)
        conn.execute("delete from timetable_block where id::text = %s", (c.id,))
        return _json(old), None
    if (c.on_date is None) == (c.weekday is None):
        raise Refused("Block either one date or a weekday, not both and not neither.")
    if c.on_date is not None and c.on_date.isoweekday() > 5:
        raise Refused("School runs Monday to Friday: that date is a weekend.")
    if c.weekday is not None and not 1 <= c.weekday <= 5:
        raise Refused("A weekday is 1 (Monday) to 5 (Friday).")
    if c.week_code not in (None, "A", "B") or (c.week_code and c.weekday is None):
        raise Refused("Week A or B applies to a weekday, not to one date.")
    if not (c.reason or "").strip():
        raise Refused("Say why the day or period is blocked.")
    if c.period_id:
        _own_period(conn, k, c.period_id)
    try:
        new = conn.execute(
            "insert into timetable_block (tenant_id, school_class_id, on_date, weekday, week_code, period_id, reason)"
            f" select tenant_id, id, %s, %s, %s, %s, %s from school_class where id = %s returning {cols}",  # noqa: S608
            (c.on_date, c.weekday, c.week_code, c.period_id, (c.reason or "").strip(), k["id"]),
        ).fetchone()
    except psycopg.errors.UniqueViolation as no:
        raise Refused("That is already blocked.", 409) from no
    return None, _json(new)


def _limit(conn: db.Conn, k: dict, c: Change) -> tuple[dict | None, dict | None]:
    cols = "id::text as id, subject_code, span, fewest, most"
    if c.action == "remove":
        old = conn.execute(
            f"select {cols} from timetable_limit where id::text = %s and school_class_id = %s",
            (c.id, k["id"]),
        ).fetchone()  # noqa: S608
        if old is None:
            raise Refused("That limit is not there.", 404)
        conn.execute("delete from timetable_limit where id::text = %s", (c.id,))
        return dict(old), None
    if c.span not in ("week", "fortnight"):
        raise Refused("A limit is for a week or for a fortnight.")
    if c.subject_code not in {s["code"] for s in _subjects(conn, k["id"])[0]}:
        raise Refused("That subject has no period in this class's timetable.")
    if c.fewest is None and c.most is None:
        raise Refused("Give the fewest, the most, or both.")
    if any(n is not None and n < 0 for n in (c.fewest, c.most)):
        raise Refused("A number of periods cannot be below zero.")
    if c.fewest is not None and c.most is not None and c.fewest > c.most:
        raise Refused("The fewest cannot be more than the most.")
    old = conn.execute(
        f"select {cols} from timetable_limit where school_class_id = %s and subject_code = %s and span = %s",
        (k["id"], c.subject_code, c.span),
    ).fetchone()  # noqa: S608
    new = conn.execute(
        "insert into timetable_limit (tenant_id, school_class_id, subject_code, span, fewest, most)"
        " select tenant_id, id, %s, %s, %s, %s from school_class where id = %s"
        " on conflict (school_class_id, subject_code, span) do update set fewest = excluded.fewest, most = excluded.most"
        f" returning {cols}",  # noqa: S608
        (c.subject_code, c.span, c.fewest, c.most, k["id"]),
    ).fetchone()
    return (dict(old) if old else None), (dict(new) if new else None)


def _fixed_slot(row: dict | None) -> dict | None:
    if row is None:
        return None
    return {"id": row["id"], "period_id": row["period_id"], "weekday": row["weekday"], "week": row["week_code"], "kind": row["kind"],
            "text": row["text"], "valid_from": row["valid_from"].isoformat()}  # fmt: skip


_SLOT = (
    "id::text as id, period_id::text as period_id, weekday, week_code, kind, text, valid_from, subject_code"
)


def _end(conn: db.Conn, slot: dict, today: dt.date) -> None:
    """A slot stops being open: yesterday is its last day, or it never started and goes."""
    if slot["valid_from"] >= today:
        conn.execute("delete from timetable_slot where id::text = %s", (slot["id"],))
    else:
        conn.execute(
            "update timetable_slot set valid_to = %s where id::text = %s",
            (today - dt.timedelta(days=1), slot["id"]),
        )


def _fixed_rule(conn: db.Conn, k: dict, c: Change, today: dt.date) -> tuple[dict | None, dict | None]:
    if c.action == "remove":
        old = conn.execute(
            f"select {_SLOT} from timetable_slot where id::text = %s and school_class_id = %s and kind = 'fixed' and valid_to is null",
            (c.id, k["id"]),
        ).fetchone()  # noqa: S608
        if old is None:
            raise Refused("That fixed slot is not there.", 404)
        _end(conn, old, today)
        return _fixed_slot(old), None
    _own_period(conn, k, c.period_id)
    if c.week_code not in ("A", "B") or c.weekday is None or not 1 <= c.weekday <= 5:
        raise Refused("A fixed slot is a period on a weekday of week A or week B.")
    if not (c.text or "").strip():
        raise Refused("Say what is fixed there.")
    old = conn.execute(
        f"select {_SLOT} from timetable_slot where school_class_id = %s and period_id::text = %s and week_code = %s"  # noqa: S608
        " and weekday = %s and valid_to is null",
        (k["id"], c.period_id, c.week_code, c.weekday),
    ).fetchone()
    if old:
        _end(conn, old, today)
    new = conn.execute(
        "insert into timetable_slot (tenant_id, school_class_id, period_id, week_code, weekday, kind, text, valid_from)"
        f" select tenant_id, id, %s, %s, %s, 'fixed', %s, %s from school_class where id = %s returning {_SLOT}",  # noqa: S608
        (c.period_id, c.week_code, c.weekday, (c.text or "").strip(), today, k["id"]),
    ).fetchone()
    return _fixed_slot(old), _fixed_slot(new)


def change(conn: db.Conn, staff: Any, class_id: str | None, c: Change, today: dt.date) -> dict:
    """One change, checked, written and kept with who made it. A refusal writes nothing."""
    k = klass(conn, class_id)
    if c.rule not in ("period", "block", "limit", "fixed") or c.action not in ("set", "remove"):
        raise Refused("That is not a rule I know.")
    with conn.transaction():
        if c.rule == "period":
            before, after = _period(conn, k, c)
        elif c.rule == "block":
            before, after = _block(conn, k, c)
        elif c.rule == "limit":
            before, after = _limit(conn, k, c)
        else:
            before, after = _fixed_rule(conn, k, c, today)
        # a period is the grade's, so every class of the grade it changes for keeps the change in its own history
        for each in [x for x in classes(conn) if x["grade"] == k["grade"]] if c.rule == "period" else [k]:
            _kept(conn, each, staff, c.rule, c.action, before, after)
    return read(conn, k["id"], staff)
