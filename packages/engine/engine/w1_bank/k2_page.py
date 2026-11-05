"""A K2 page as a screen reads it (goals/m1-12b-apply-and-edit.yaml, task M1-12b): the eight parts, each with its words
and who they are from, the steps as bullets and the thinking as an idea and slips, the materials as items, and what the
maker and the checker said of the draft. Reads only. A list stored beside a part is used only while it reads out as the
part's text (`render`): a text changed any other way leaves a stale list, and the text wins.
"""

import re

from engine.core import db
from engine.w1_bank.k2_format import LISTS, lines_of, render
from engine.w1_bank.k2_gaps import PARTS

KINDS = {"steps": "bullets", "thinking": "thinking"}


def _part(part: str, row: dict, source: str, check_me: bool) -> dict:
    text = (row[part] or "").strip()
    listed = row.get(LISTS.get(part, ""))
    out: dict = {
        "part": part, "kind": KINDS.get(part, "text"), "source": source if text else "", "check_me": check_me,
        "text": text, "items": [], "idea": None, "slips": [],
    }  # fmt: skip
    if part == "steps":
        out["items"] = listed if listed and render(part, listed) == text else lines_of(text)
    if part == "thinking" and listed and render(part, listed) == text:
        out["idea"], out["slips"] = listed["idea"], listed["slips"]
    return out


def read(conn: db.Conn, tenant: db.Id, code: str) -> dict:
    """The page `code`: raises LookupError if the school has no such activity."""
    row = conn.execute(
        "select code, name, strand, materials, objective, steps, thinking, level_0, level_1, level_2, level_3,"
        " steps_list, thinking_doc from activity where tenant_id = %s and code = %s",
        (tenant, code),
    ).fetchone()
    if row is None:
        raise LookupError(f"no activity {code}")
    marks = {
        r["part"]: r
        for r in conn.execute(
            "select part, source, check_me from activity_part_source where tenant_id = %s and activity_code = %s",
            (tenant, code),
        ).fetchall()
    }
    parts = [
        _part(p, {**row, "steps_list": row["steps_list"], "thinking_doc": row["thinking_doc"]},
              marks[p]["source"] if p in marks else "school", bool(p in marks and marks[p]["check_me"]))
        for p in PARTS
        if p != "materials"
    ]  # fmt: skip
    items = conn.execute(
        "select i.name, m.quantity, i.unit from activity_material m join material_item i on i.tenant_id = m.tenant_id"
        " and i.code = m.material_code where m.tenant_id = %s and m.activity_code = %s order by m.ord",
        (tenant, code),
    ).fetchall()
    draft = conn.execute(
        "select p.id, p.proposer, p.validator, p.verdict, p.reason, p.proposal->'history' as history, n.status as now"
        " from curriculum_proposal p join lateral (select status from curriculum_proposal x where x.tenant_id = p.tenant_id"
        " and (x.id = p.id or x.about = p.id) order by x.created_at desc, x.id limit 1) n on true"
        " where p.tenant_id = %s and p.kind = 'page_part' and p.subject_code = %s and p.about is null"
        " order by p.created_at desc limit 1",
        (tenant, code),
    ).fetchone()
    return {
        "code": code, "name": row["name"], "section": row["strand"], "parts": parts,
        "materials": {"text": (row["materials"] or "").strip(), "items": [dict(i) for i in items]},
        "draft": None if draft is None else {
            "maker": draft["proposer"], "checker": draft["validator"], "verdict": draft["verdict"],
            "reason": re.sub(r"\s+", " ", draft["reason"]).strip(), "history": draft["history"] or [],
            "status": draft["now"],
        },
    }  # fmt: skip
