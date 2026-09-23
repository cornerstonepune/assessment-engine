"""W2 — one paper per child, and the pack the teacher carries.

A child's paper is a worksheet from the library (ADR 0026, step 7): each child is handed a worksheet
at their skill and level that they have never sat, holding no question they saw inside the exposure
window and none another child has this week — so copying from a neighbour gains nothing while the
teacher still holds one key per worksheet. A worksheet is never edited once made; what was printed
for one child, its page geometry, is kept on that child's sheet instance.
"""

import hashlib
import json
import shutil
from pathlib import Path

from playwright.sync_api import sync_playwright

from engine.assess.pick import Sheet
from engine.assess.render import render_sheet
from engine.core import db, roster
from engine.w1_bank.inventory import item_from_row
from engine.w2_print import pack


def _config(conn, key, default):
    row = conn.execute("select value from config where key = %s", (key,)).fetchone()
    return row["value"] if row else default


def _threshold(conn, key, default):
    row = conn.execute("select value from threshold where key = %s", (key,)).fetchone()
    return float(row["value"]) if row else default


def _qr(*parts) -> str:
    """The code printed on the page. Opaque on purpose: it resolves to a row, and carries no
    child, level or answer of its own."""
    return "CS" + hashlib.sha1("|".join(map(str, parts)).encode()).hexdigest()[:6].upper()


def _worksheets(conn, skill_set, difficulty, child_id, window_days):
    """The library's worksheets at this skill and level a child may be given, least handed out first:
    never one the child sat, never one holding a question they saw inside the exposure window, never
    one holding a question that has left the bank. With no child — a spare — only the last applies."""
    return conn.execute(
        "select t.id, t.code, t.item_ids from sheet_template t"
        " where t.source = 'library' and t.retired_at is null"
        "   and t.skill_set_code = %s and t.difficulty = %s"
        "   and not exists (select 1 from item i where i.id = any(t.item_ids) and i.status <> 'active')"
        "   and not exists (select 1 from sheet_instance si where si.sheet_template_id = t.id and si.child_id = %s)"
        "   and not exists (select 1 from item_exposure x where x.item_id = any(t.item_ids)"
        "                   and x.child_id = %s and x.created_at > now() - make_interval(days => %s))"
        " order by (select count(*) from sheet_instance si where si.sheet_template_id = t.id), t.code",
        (skill_set, difficulty, child_id, child_id, int(window_days)),
    ).fetchall()


def _why_short(conn, p, window_days):
    """Why this child could not be given a worksheet, in words — never a short paper or a repeat."""
    n = conn.execute(
        "select count(*) as level, count(*) filter (where exists (select 1 from sheet_instance si"
        "   where si.sheet_template_id = t.id and si.child_id = %s)) as sat"
        " from sheet_template t where t.source = 'library' and t.retired_at is null"
        "   and t.skill_set_code = %s and t.difficulty = %s"
        "   and not exists (select 1 from item i where i.id = any(t.item_ids) and i.status <> 'active')",
        (p["child_id"], p["skill_set_code"], p["difficulty"]),
    ).fetchone()
    if not n["level"]:
        return "the library holds no worksheet at this level yet: run engine library build"
    if n["sat"] >= n["level"]:
        return f"has sat every worksheet at {p['difficulty']} ({n['level']})"
    return (
        "every worksheet left shares a question with another child's paper this week, or holds one"
        f" this child saw in the last {int(window_days)} days"
    )


def for_week(conn, section: str, week: str, kind: str = "practice") -> dict:
    """Hand every prescription in the section this week a worksheet from the library, plus the spares.

    No two children share a question, and what each child was shown is recorded. A child who cannot
    be given one is named with the reason, never handed a short paper or a repeat.
    """
    tenant = conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]
    spares_each = int(_config(conn, "assemble.spares_per_difficulty", 2))
    window = _threshold(conn, "exposure.days", 21)

    rx = conn.execute(
        "select p.id, p.child_id, p.skill_set_code, p.difficulty, p.rule_fired, c.roll_no, c.band"
        " from prescription p join child c on c.id = p.child_id"
        " where c.section = %s and p.week = %s and p.kind = %s"
        " order by coalesce(nullif(regexp_replace(c.roll_no, '\\D', '', 'g'), '')::int, 9999), c.roll_no",
        (section, week, kind),
    ).fetchall()
    if not rx:
        raise ValueError(f"no prescriptions for {section} {week} {kind} — run prescribe first")

    into = {"section": section, "week": week, "kind": kind}  # the pack every paper here belongs to
    given: set = set()  # worksheets handed out this week
    used: set = set()  # their questions — no two children share one
    built, short = [], []
    for p in rx:
        w = next(
            (
                w
                for w in _worksheets(conn, p["skill_set_code"], p["difficulty"], p["child_id"], window)
                if w["id"] not in given and not used.intersection(w["item_ids"])
            ),
            None,
        )
        if w is None:
            short.append(
                {
                    "roll_no": p["roll_no"],
                    "child_id": p["child_id"],
                    "difficulty": p["difficulty"],
                    "had": 0,  # worksheets this child could still be given
                    "needed": 1,
                    "why": _why_short(conn, p, window),
                }
            )
            continue
        given.add(w["id"])
        used.update(w["item_ids"])
        built.append(_hand_out(conn, tenant, into, p, w))

    spares = []
    for difficulty in sorted({p["difficulty"] for p in rx}):
        first = next(p for p in rx if p["difficulty"] == difficulty)
        for w in _worksheets(conn, first["skill_set_code"], difficulty, None, window):
            if len([s for s in spares if s["difficulty"] == difficulty]) == spares_each:
                break
            if w["id"] in given or used.intersection(w["item_ids"]):
                continue
            given.add(w["id"])
            used.update(w["item_ids"])
            n = 1 + len([s for s in spares if s["difficulty"] == difficulty])
            spare = {
                "id": None,
                "child_id": None,
                "skill_set_code": first["skill_set_code"],
                "difficulty": difficulty,
                "band": first["band"],
                "roll_no": f"spare {n}",
                "rule_fired": "spare",
            }
            spares.append(_hand_out(conn, tenant, into, spare, w))

    return {"sheets": built, "spares": spares, "short": short}


def _hand_out(conn, tenant, into, p, w):
    """One library worksheet given to one child, or kept as a spare: a new sheet instance — the code on
    the page — pointing at the worksheet, which is never edited."""
    # The section is in the code because two classes can be handed the same worksheet in one week.
    qr = _qr(w["id"], p["child_id"], into["section"], p["roll_no"], into["week"], into["kind"])
    instance = conn.execute(
        "insert into sheet_instance (tenant_id, qr_code, sheet_template_id, child_id, week, section, kind)"
        " values (%s,%s,%s,%s,%s,%s,%s) returning id, qr_code",
        (tenant, qr, w["id"], p["child_id"], into["week"], into["section"], into["kind"]),
    ).fetchone()
    if p["id"]:
        conn.execute(
            "update prescription set sheet_instance_id = %s where id = %s", (instance["id"], p["id"])
        )
    if p["child_id"]:
        # One ordered statement, not a loop: two classes assembled at the same moment insert into the
        # same index pages, and doing it in each child's own sample order deadlocked (the pair that
        # `test_two_classes_assembled_at_the_same_moment_both_finish` catches). Ordering by item id
        # makes every builder touch the index the same way round — and it is one round trip, not
        # twelve.
        conn.execute(
            "insert into item_exposure (tenant_id, child_id, item_id, week)"
            " select %s, %s, id, %s from unnest(%s::uuid[]) as id order by id"
            " on conflict (tenant_id, child_id, item_id) do nothing",
            (tenant, p["child_id"], into["week"], list(w["item_ids"])),
        )
    # `item.times_used` is NOT written here. It is a derived number — how often a question has been
    # handed out, which `item_exposure` already records row by row — and writing it from the hot path
    # made two classes assembled at the same moment deadlock on the same item rows (Postgres locks in
    # scan order, so even an ordered `for update` did not fix it). Ring B owns derived numbers:
    # `engine graph` refreshes the counter from the exposures.
    rows = {r["id"]: r for r in conn.execute("select * from item where id = any(%s)", (list(w["item_ids"]),))}
    return {
        "template_id": w["id"],
        "code": w["code"],
        "instance_id": instance["id"],
        "qr": instance["qr_code"],
        "child_id": p["child_id"],
        "roll_no": p["roll_no"],
        "band": p["band"],
        "skill_set_code": p["skill_set_code"],
        "difficulty": p["difficulty"],
        "rule": p["rule_fired"],
        "item_rows": [rows[i] for i in w["item_ids"]],
    }


def made(conn, section: str, week: str, kind: str = "practice") -> dict:
    """The pack already made for a class's week, in handout order, shaped as `for_week` returns it — so a pack is
    drawn as it was made. Rendering never assembles again: that handed every child a second paper."""
    papers = pack.papers(conn, section, week, kind)
    if not papers:
        raise ValueError(f"no papers made for {section} {week} {kind} — assemble first")
    detail = {
        r["qr_code"]: r
        for r in conn.execute(
            "select si.qr_code, si.id as instance_id, st.band, st.code, st.skill_set_code, st.difficulty, st.item_ids"
            " from sheet_instance si join sheet_template st on st.id = si.sheet_template_id where si.qr_code = any(%s)",
            ([p["qr_code"] for p in papers],),
        )
    }
    ids = list({i for d in detail.values() for i in d["item_ids"]})
    rows = {r["id"]: r for r in conn.execute("select * from item where id = any(%s)", (ids,))}
    out = {"sheets": [], "spares": [], "short": []}
    for p in papers:
        d = detail[p["qr_code"]]
        sheet = {**d, "qr": p["qr_code"], "child_id": p["child_id"], "roll_no": p["roll_no"]}
        sheet["item_rows"] = [rows[i] for i in d["item_ids"]]
        out["sheets" if p["child_id"] else "spares"].append(sheet)
    return out


def label(name, s, kind):
    """The line printed at the top of a child's page: who it is for, the level, and which worksheet it
    is — so anyone holding the paper can say which one the child had."""
    return f"{name} · {s['difficulty']} {kind} · Worksheet {s['code']}"


def render(conn, built: dict, outdir: Path, week: str, actor: str, kind: str = "practice") -> dict:
    """Render every sheet to PDF, write each key, and merge one pack in handout order.

    The child's name is printed on their own page and nowhere else — it is read through the
    logging accessor, and never stored outside `pii`.
    """
    outdir = Path(outdir)
    if outdir.exists():
        shutil.rmtree(outdir)
    outdir.mkdir(parents=True)
    sheets = built["sheets"] + built["spares"]
    named = roster.names(conn, [s["child_id"] for s in sheets if s["child_id"]], actor)
    titles = {r["code"]: r["name"] for r in conn.execute("select code, name from skill_set").fetchall()}

    pdfs = []
    with sync_playwright() as pw:
        for s in sheets:
            items = [item_from_row(r) for r in s["item_rows"]]
            sh = Sheet(s["qr"], s["band"], s["difficulty"], 1, week, items, title=titles[s["skill_set_code"]])
            key = render_sheet(
                sh, outdir, week_label=label(named.get(s["child_id"], "Spare copy"), s, kind), pw=pw
            )
            # What was printed for this child, on this child's instance — the worksheet stays as made.
            conn.execute(
                "update sheet_instance set pdf_path = %s, key = %s where id = %s",
                (str(outdir / f"{s['qr']}.pdf"), json.dumps(key), s["instance_id"]),
            )
            pdfs.append(str(outdir / f"{s['qr']}.pdf"))
            s["pages"] = key["pages"]

    merged = pack.merge(pdfs, outdir / f"{week}_pack.pdf")
    return {
        "pack": str(merged),
        "sheets": len(built["sheets"]),
        "spares": len(built["spares"]),
        "pages": sum(s["pages"] for s in sheets),
    }
