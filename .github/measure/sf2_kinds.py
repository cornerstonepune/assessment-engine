"""SF2, measured on a copy of live before the build: what approval per skill × kind would take off papers."""

from collections import defaultdict

from engine.core import db
from engine.w2_print import shelf

with db.connect() as c:
    levels = c.execute(
        "select s.code, d.key as level, s.level_approved ? d.key as ok, s.status from skill s, jsonb_each(s.difficulty) d"
    ).fetchall()
    ok = {(r["code"], r["level"]): r["ok"] for r in levels}
    kinds = c.execute(
        "select skill_set_code as s, difficulty as l, template as k, fmt as f, count(*)::int as n from item"
        " where status = 'active' group by 1, 2, 3, 4"
    ).fetchall()
    closing = shelf.closing(c)
pairs = defaultdict(set)
for r in kinds:
    pairs[(r["s"], r["k"])].add(r["l"])
print(
    f"skills {len({r['code'] for r in levels})} · ratified {len({r['code'] for r in levels if r['status'] == 'ratified'})}"
)
print(f"levels {len(levels)} · approved {sum(1 for r in levels if r['ok'])}")
print(
    f"skill x template {len(pairs)} · skill x format {len({(r['s'], r['f']) for r in kinds})}"
    f" · skill x level x template {len(kinds)} · questions {sum(r['n'] for r in kinds)}"
)
every = [p for p, ls in pairs.items() if all(ok.get((p[0], lv)) for lv in ls)]
some = [p for p, ls in pairs.items() if any(ok.get((p[0], lv)) for lv in ls) and p not in every]
print(
    f"pairs whose every level is approved {len(every)} · some {len(some)} · none {len(pairs) - len(every) - len(some)}"
)
shut = {(r["skill"], r["level"]) for r in closing}
by_level = defaultdict(list)
for r in kinds:
    if (r["s"], r["l"]) in shut:
        by_level[(r["s"], r["l"])].append((r["k"], r["n"], r["f"]))
need = {(s, k) for (s, lv), ks in by_level.items() for k, _, _ in ks}
need_fmt = {(s, f) for (s, lv), ks in by_level.items() for _, _, f in ks}
need_any = {f for _, f in need_fmt}
print(
    f"on a class's paper today and not approved: {len(shut)} levels in {len({s for s, _ in shut})} skills,"
    f" {sum(n for ks in by_level.values() for _, n, _ in ks)} questions, {len({r['class'] for r in closing})} classes"
)
print(
    f"  approvals to open them again: level by level {len(shut)} · by template {len(need)} · skill x format {len(need_fmt)} · format alone {len(need_any)}"
)
for (s, lv), ks in sorted(by_level.items()):
    cls = sorted({r["class"] for r in closing if (r["skill"], r["level"]) == (s, lv)})
    where = ", ".join(cls) if len(cls) <= 6 else f"{len(cls)} classes"
    print(f"  {s:<14}{lv:<9}{', '.join(f'{f}:{k} {n}' for k, n, f in sorted(ks))}  · {where}")
