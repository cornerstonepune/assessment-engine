"""B2, measured on a copy of live before its goal is written: the question types in use, on which levels, which are
approved, which labels lack words, and what gating on confirmed levels and approved types would take off papers today.

A type (decision B2-1, ADR 0077): the printed format where the template is only the level's numbers written as a name
(ADD.2D2D.REG1, MUL.3D1D, ADD.MULTI3), else the template itself (EQ.TRUE_FALSE, MULT.NTH, SEQ.ON).
Nothing is written. Codes and counts only; no child is named.
"""

import json
import re
from collections import defaultdict
from pathlib import Path

from engine.core import db
from engine.w2_print import shelf

NUMBERS = re.compile(r"^(ADD|SUB|MUL|DIV)\.(\dD\dD(\.REG\w*)?|MULTI\d*)$")
seeded = Path(__file__).resolve().parents[2] / "supabase/seed/question_types.json"
TYPES = json.loads(seeded.read_text())["question_types"]
SEEDED = {t["code"] for t in TYPES}
KIND = {t["fmt"] for t in TYPES}  # the labels that have words (until B2, the website's `KIND`)


def type_of(r):
    return r["fmt"] if NUMBERS.match(r["template"] or "") else r["template"]


with db.connect() as c:
    ok = {
        (r["code"], r["level"]): r["ok"]
        for r in c.execute(
            "select s.code, d.key as level, s.level_approved ? d.key as ok from skill_set s, jsonb_each(s.difficulty) d"
        )
    }
    rows = c.execute(
        "select skill_set_code as s, difficulty as l, template, fmt, count(*)::int as n from item"
        " where status = 'active' and source = 'generated' group by 1, 2, 3, 4"
    ).fetchall()
    printed = c.execute(
        "select distinct i.template, i.fmt from sheet_instance si join sheet_template t on t.id = si.sheet_template_id,"
        " unnest(t.item_ids) x(id) join item i on i.id = x.id where i.source = 'generated'"
    ).fetchall()
    on_library = c.execute(
        "select distinct i.template, i.fmt from sheet_template t, unnest(t.item_ids) x(id) join item i on i.id = x.id"
        " where t.source = 'library' and t.retired_at is null and i.source = 'generated'"
    ).fetchall()
    lists = c.execute("select code, formats from skill_set").fetchall()
    level_formats = c.execute(
        "select distinct d.value -> 'check' ->> 'format' as f from skill_set s, jsonb_each(s.difficulty) d"
    ).fetchall()
    closing = shelf.closing(c)
    b2 = c.execute("select to_regclass('public.question_type') is not null as built").fetchone()["built"] and c.execute(
        "select (select count(*) from question_type)::int as types,"
        " (select count(*) from question_type_approval)::int as approved,"
        " (select count(*) from skill_level_question_type)::int as links,"
        " (select count(*) from item where status = 'active' and source = 'generated')::int as active,"
        " (select count(*) from drawable_item where source = 'generated')::int as drawable"
    ).fetchone()
    ev = c.execute(
        "select count(*)::int as n, md5(coalesce(string_agg(e::text, '|' order by e.id), '')) as sum"
        " from evidence_event e"
    ).fetchone()

uses, qs = defaultdict(set), defaultdict(int)
for r in rows:
    uses[type_of(r)].add((r["s"], r["l"]))
    qs[type_of(r)] += r["n"]
levels = {x for u in uses.values() for x in u}
print(
    f"types in use {len(uses)} · skill x type {len({(s, f) for f, u in uses.items() for s, _ in u})}"
    f" · level x type {sum(len(u) for u in uses.values())} · levels holding questions {len(levels)}"
    f" · levels {len(ok)}, approved {sum(ok.values())}"
)
every = {f for f, u in uses.items() if all(ok.get(x) for x in u)}
on_paper = {type_of(r) for r in printed} | {type_of(r) for r in on_library}
print(
    f"types whose every level is approved {len(every)} · on a printed or library paper {len(on_paper & set(uses))}"
    f" · start approved (either) {len(every | (on_paper & set(uses)))} · would wait {len(set(uses) - every - on_paper)}"
)
for f in sorted(set(uses) - every - on_paper):
    print(f"  waits: {f:<30} levels {len(uses[f])} questions {qs[f]}")
for f in sorted(set(uses) - every):
    u = uses[f]
    print(f"  not every level approved: {f:<30} levels {len(u)}, approved {sum(1 for x in u if ok.get(x))}")
fmts = {r["fmt"] for r in rows}
listed = {f for r in lists for f in r["formats"]}
print(f"labels the bank holds {len(fmts)} · in the skills' lists {len(listed)} · with words {len(KIND)}")
print(f"  held or listed, no words: {sorted((fmts | listed) - KIND)}")
print(f"  words, held by no question: {sorted(KIND - fmts)} · words, on no list: {sorted(KIND - listed)}")
print(f"  a level's own format, no words: {sorted({r['f'] for r in level_formats if r['f']} - KIND)}")
print(f"types held that the seed has no row for: {sorted(set(uses) - SEEDED)} · seed rows held nowhere: {sorted(SEEDED - set(uses))}")
print(f"unconfirmed levels a class's paper may draw today: {len({(r['skill'], r['level']) for r in closing})}")
for r in sorted({(r["skill"], r["level"], r["questions"]) for r in closing}):
    print(f"  unconfirmed, drawn today: {r[0]} {r[1]} questions {r[2]}")
if b2:
    print(
        f"after B2: types {b2['types']}, approved {b2['approved']}, level x type links {b2['links']}"
        f" · the bank's active questions {b2['active']}, a paper may draw {b2['drawable']}"
    )
print(f"evidence {ev['n']} rows, checksum {ev['sum']}")
