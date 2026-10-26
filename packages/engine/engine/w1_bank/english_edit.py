"""An educator changes an English sample, or the kinds a level asks (goals/edt_edit_samples_and_kinds.yaml). Nimish,
2026-10-24: "What happens if he wants to make any changes there? … It should simply have the capability to edit the
skill, where the nature or the description of the skill can be changed."

Every save is checked by code first (english_check.py) and refused in words when it fails, with nothing stored. One
that passes is a new row of `english_sample_edit`, which keeps the sample it replaced and is never changed; the page
reads the newest (`english_sample_now`). Each change withdraws that level's approval, and no other, so the approver
reads it again. A level keeps three samples of every kind it asks and at least one kind; a kind is added only once it
is approved and has three samples that pass. A skill whose questions code makes from its levels' rules has no samples here.
"""

import json
import secrets
from dataclasses import replace
from typing import Any

from engine.core import db, english, settings
from engine.w1_bank import english_check, english_form, english_words

NUMBER_WORDS = ("none", "one", "two", "three", "four", "five", "six")
COLUMNS = (
    "ask",
    "passage_code",
    "text",
    "options",
    "answer",
    "accept",
    "rubric_code",
    "key_points",
    "not_words",
)


def few(conn: db.Conn) -> int:
    """How many samples a level keeps of each kind it asks: what an approver reads before approving it (a row)."""
    return int(settings.threshold(conn, "samples.per_kind", 3))


def _said(n: int) -> str:
    return NUMBER_WORDS[n] if 0 <= n < len(NUMBER_WORDS) else str(n)


def _hold(conn: db.Conn, code: str, level: str, kind: str) -> None:
    """One change at a time to a level's samples of a kind, so two saves at once never take the same number."""
    conn.execute("select pg_advisory_xact_lock(hashtext(%s))", (f"english_sample {code} {level} {kind}",))


def _tenant(conn: db.Conn) -> db.Id:
    return db.one(conn, "select id from tenant where slug = %s", (db.tenant_slug(),))["id"]


def is_english(conn: db.Conn, code: str) -> bool:
    row = conn.execute(
        "select t.subject_code from skill s join topic t on t.tenant_id = s.tenant_id and t.code = s.topic_code"
        " where s.code = %s",
        (code,),
    ).fetchone()
    return bool(row) and row["subject_code"] == english.SUBJECT


def current(conn: db.Conn, code: str, level: str, kind: str, ord: int) -> dict[str, Any] | None:
    """One sample as it stands: the newest edit, else the seed's; None when there is none or it was removed."""
    return conn.execute(
        "select * from english_sample_now where skill_code = %s and difficulty = %s and question_type = %s and ord = %s",
        (code, level, kind, ord),
    ).fetchone()


def _count(conn: db.Conn, code: str, level: str, kind: str) -> int:
    return db.one(
        conn,
        "select count(*) as n from english_sample_now where skill_code = %s and difficulty = %s and question_type = %s",
        (code, level, kind),
    )["n"]


def level_kinds(conn: db.Conn, code: str, level: str) -> list[str]:
    return [
        r["question_type"]
        for r in conn.execute(
            "select question_type from skill_level_question_type where skill_code = %s and difficulty = %s"
            " order by place nulls last, question_type",
            (code, level),
        )
    ]


def _context(conn: db.Conn, code: str, level: str, kind: str) -> english_check.Context | None:
    """What a sample of this level and kind is checked against (its passage aside); None when the skill has no such
    level or no such kind."""
    row = conn.execute(
        "select l.rule, 'open_response' = any(q.marked) as open,"
        " coalesce((select jsonb_object_agg(m.code, m.name) from skill_mistake k join misconception m"
        "   on m.tenant_id = k.tenant_id and m.code = k.misconception_code and m.op = k.op"
        "   where k.skill_code = l.skill_code), '{}'::jsonb) as mistakes,"
        " array(select r.code from rubric r where l.skill_code = any(r.skill_codes)) as rubrics"
        " from skill_level l join question_type q on q.tenant_id = l.tenant_id and q.code = %s"
        " where l.skill_code = %s and l.difficulty = %s",
        (kind, code, level),
    ).fetchone()
    if row is None:
        return None
    return english_check.Context(
        open=row["open"], mistakes=row["mistakes"], rule=row["rule"], rubrics=set(row["rubrics"])
    )


def _written(one: dict[str, Any]) -> tuple[str, str] | None:
    """(title, text) of a passage the educator wrote on the form, or None."""
    text = (one.get("passage_text") or "").strip()
    return ((one.get("passage_title") or "").strip(), text) if text else None


def _passage_text(conn: db.Conn, code: str | None) -> str:
    row = conn.execute("select text from passage where code = %s", (code,)).fetchone() if code else None
    return row["text"] if row else ""


def withdraw(conn: db.Conn, code: str, level: str) -> None:
    """The level waits for approval again; the database sets the skill back to waiting with it."""
    conn.execute(
        "update skill set level_approved = level_approved - %s::text, updated_at = now() where code = %s",
        (level, code),
    )


def _checked(
    conn: db.Conn, context: english_check.Context, kind: str, one: dict[str, Any]
) -> tuple[dict, dict]:
    """(the sample as it would be stored, its faults) for one sample as the form sent it."""
    s = english_form.from_form(kind, one.get("fields") or {})
    # every row of the form, empty ones too, so a fault is numbered as the form numbers its rows; stored without them
    s["wrong"] = [
        {"answer": (w.get("answer") or "").strip(), "mistake_code": w.get("mistake_code") or ""}
        for w in one.get("wrong") or []
    ]
    written = _written(one)
    s["passage_code"] = None if written else (one.get("passage_code") or None)
    s["rubric_code"] = one.get("rubric_code") or None
    passage = written[1] if written else _passage_text(conn, s["passage_code"])
    if s["passage_code"] and not passage:
        s["passage_code"] = None
    try:
        faults = english_check.faults(s, replace(context, passage=passage))
    except english_words.NoDictionary:
        return s, {
            "skill": [
                "The spelling list could not be read just now, so nothing was saved. Try again in a minute."
            ]
        }
    if written and not written[0]:
        faults.setdefault("passage", []).append("Give the passage you wrote a title.")
    return s, faults


def _snapshot(row: dict[str, Any] | None) -> str | None:
    return json.dumps({k: row[k] for k in (*COLUMNS, "wrong")}) if row else None


def _ledger(
    conn: db.Conn, t: db.Id, slot: tuple[str, str, str, int], by: str, sample: dict | None, was: dict | None
) -> None:
    """One version of one sample: the sample as saved, or none for a removal; what it replaced; who."""
    conn.execute(
        "insert into english_sample_edit (tenant_id, skill_code, difficulty, question_type, ord, removed, sample,"
        " replaced, edited_by) values (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (t, *slot, sample is None, json.dumps(sample) if sample else None, _snapshot(was), by),
    )


def _store(
    conn: db.Conn, t: db.Id, slot: tuple[str, str, str, int], s: dict, one: dict, by: str, was: dict | None
) -> None:
    code = slot[0]
    if written := _written(one):
        s["passage_code"] = f"P.ED.{code}.{secrets.token_hex(3)}"
        conn.execute(
            "insert into passage (tenant_id, code, grade, kind, title, text)"
            " select %s, %s, s.grade, 'written by an educator', %s, %s from skill s where s.code = %s",
            (t, s["passage_code"], *written, code),
        )
    keep = {k: s.get(k) for k in COLUMNS} | {"wrong": [w for w in s["wrong"] if w["answer"]]}
    _ledger(conn, t, slot, by, keep, was)


def _next_ord(conn: db.Conn, code: str, level: str, kind: str) -> int:
    return db.one(
        conn,
        "select coalesce(max(ord), 0) + 1 as n from (select ord from english_sample where skill_code = %s and"
        " difficulty = %s and question_type = %s union all select ord from english_sample_edit where skill_code = %s"
        " and difficulty = %s and question_type = %s) o",
        (code, level, kind, code, level, kind),
    )["n"]


def save(
    conn: db.Conn, code: str, level: str, kind: str, ord: int | None, by: str, **one: Any
) -> dict[str, Any]:
    """One sample saved: changed where `ord` names one, added where it is None. {saved, ord, faults}."""

    def refuse(faults: dict[str, list[str]]) -> dict[str, Any]:
        return {"saved": False, "ord": ord, "faults": faults}

    if not is_english(conn, code):
        return refuse(
            {"skill": ["This skill's questions are made by code from each level's rule, not edited here."]}
        )
    if kind not in level_kinds(conn, code, level):
        return refuse({"skill": ["This level does not ask that kind of question."]})
    _hold(conn, code, level, kind)
    was = current(conn, code, level, kind, ord) if ord is not None else None
    if ord is not None and not was:
        return refuse({"skill": ["That sample is not on this level any more."]})
    context = _context(conn, code, level, kind)
    if context is None:
        return refuse({"skill": ["This skill has no such level or kind of question."]})
    s, faults = _checked(conn, context, kind, one)
    if faults:
        return refuse(faults)
    ord = ord or _next_ord(conn, code, level, kind)
    _store(conn, _tenant(conn), (code, level, kind, ord), s, one, by, was)
    withdraw(conn, code, level)
    return {"saved": True, "ord": ord, "faults": {}}


def remove(conn: db.Conn, code: str, level: str, kind: str, ord: int, by: str) -> dict[str, Any]:
    """One sample taken off its level: a version that says so, the sample kept in what it replaced."""
    was = current(conn, code, level, kind, ord)
    if not was or not is_english(conn, code):
        return {"removed": False, "why": "That sample is not on this level any more."}
    _hold(conn, code, level, kind)
    if _count(conn, code, level, kind) <= (n := few(conn)):
        return {
            "removed": False,
            "why": f"A level keeps at least {_said(n)} samples of each kind it asks; add one first.",
        }
    _ledger(conn, _tenant(conn), (code, level, kind, ord), by, None, was)
    withdraw(conn, code, level)
    return {"removed": True, "why": ""}


def approved_kinds(conn: db.Conn) -> list[dict[str, Any]]:
    """The kinds an English level may be given (`level_kind_choice`, which the website offers from too)."""
    return conn.execute(
        "select code, words from level_kind_choice where subject_code = %s order by words", (english.SUBJECT,)
    ).fetchall()


def _kind_changed(conn: db.Conn, code: str, level: str, kind: str, added: bool, by: str) -> None:
    conn.execute(
        "insert into skill_level_kind_change (tenant_id, skill_code, difficulty, question_type, added, changed_by)"
        " values (%s, %s, %s, %s, %s, %s)",
        (_tenant(conn), code, level, kind, added, by),
    )


def add_kind(conn: db.Conn, code: str, level: str, kind: str, samples: list[dict], by: str) -> dict[str, Any]:
    """A kind added to a level, with the samples it needs to have three that pass. {saved, why, faults per sample}."""

    def refuse(why: str, faults: list | None = None) -> dict[str, Any]:
        return {"saved": False, "why": why, "faults": faults or []}

    if not is_english(conn, code):
        return refuse("This skill's kinds follow its questions, which code makes.")
    if kind not in {k["code"] for k in approved_kinds(conn)}:
        return refuse("Only a kind of question that has been approved can be added.")
    if kind in level_kinds(conn, code, level):
        return refuse("This level already asks that kind.")
    context = _context(conn, code, level, kind)
    if context is None:
        return refuse("This skill has no such level or kind of question.")
    _hold(conn, code, level, kind)
    n = few(conn)
    if len(samples) < n - _count(conn, code, level, kind):
        return refuse(f"Add {_said(n)} samples for this kind: a level shows {_said(n)} of each.")
    checked = [_checked(conn, context, kind, one) for one in samples]
    if any(f for _, f in checked):
        return refuse("A sample did not pass its checks.", [f for _, f in checked])
    t, first = _tenant(conn), _next_ord(conn, code, level, kind)
    for i, ((s, _), one) in enumerate(zip(checked, samples, strict=True)):
        _store(conn, t, (code, level, kind, first + i), s, one, by, None)
    conn.execute(
        "insert into skill_level_question_type (tenant_id, skill_code, difficulty, question_type)"
        " select tenant_id, skill_code, difficulty, %s from skill_level where skill_code = %s and difficulty = %s"
        " on conflict do nothing",
        (kind, code, level),
    )
    _kind_changed(conn, code, level, kind, True, by)
    withdraw(conn, code, level)
    return {"saved": True, "why": "", "faults": []}


def remove_kind(conn: db.Conn, code: str, level: str, kind: str, by: str) -> dict[str, Any]:
    """A kind taken from a level; its samples stay stored, off the page. A level keeps at least one kind."""
    kinds = level_kinds(conn, code, level)
    if not is_english(conn, code) or kind not in kinds:
        return {"removed": False, "why": "This level does not ask that kind."}
    if len(kinds) == 1:
        return {"removed": False, "why": "A level asks at least one kind of question; add another first."}
    conn.execute(
        "delete from skill_level_question_type where skill_code = %s and difficulty = %s and question_type = %s",
        (code, level, kind),
    )
    _kind_changed(conn, code, level, kind, False, by)
    withdraw(conn, code, level)
    return {"removed": True, "why": ""}


def check(conn: db.Conn, code: str, level: str, kind: str, s: dict[str, Any]) -> dict[str, list[str]]:
    """The faults of a question in the stored shape (`english_sample_now`'s), as a sample of this level and kind is
    checked before it is stored: {field: [what is wrong, in words]}, empty when it may be stored."""
    context = _context(conn, code, level, kind)
    if context is None:
        return {"skill": ["This skill has no such level or kind of question."]}
    try:
        return english_check.faults(
            {**s, "question_type": kind}, replace(context, passage=_passage_text(conn, s.get("passage_code")))
        )
    except english_words.NoDictionary:
        return {
            "skill": [
                "The spelling list could not be read just now, so nothing was saved. Try again in a minute."
            ]
        }


def made(
    conn: db.Conn, code: str, level: str, kind: str, ord: int, samples: list[dict], by: str, run: db.Id | None
) -> list[int]:
    """Questions made from sample `ord` that passed `check`: each a new sample of its own, saying what it was made from
    and the model's run that wrote it, a draft until the level is approved again. Their numbers."""
    _hold(conn, code, level, kind)
    t, first = _tenant(conn), _next_ord(conn, code, level, kind)
    for i, s in enumerate(samples):
        conn.execute(
            "insert into english_sample_edit (tenant_id, skill_code, difficulty, question_type, ord, sample, edited_by,"
            " made_from, flow_run_id) values (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (
                t,
                code,
                level,
                kind,
                first + i,
                json.dumps({k: s.get(k) for k in (*COLUMNS, "wrong")}),
                by,
                ord,
                run,
            ),
        )
    if samples:
        withdraw(conn, code, level)
    return list(range(first, first + len(samples)))
