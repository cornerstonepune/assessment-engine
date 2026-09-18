"""W2 — one paper per child, and the pack the teacher carries.

Every child at the same difficulty gets a different paper: the picker is seeded from the child, so
copying from a neighbour gains nothing while the teacher still holds one key. A child never sees
the same question twice inside the exposure window, which is what makes a second attempt evidence
rather than recall.
"""
import hashlib
import json
import random
import shutil
import subprocess
from pathlib import Path

from playwright.sync_api import sync_playwright

from engine import db, roster
from engine.assess.pick import Sheet
from engine.assess.render import render_sheet
from engine.bank import item_from_row


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


def _available(conn, skill_set, difficulty, child_id, window_days):
    """Active items for this set and difficulty that this child has not seen inside the window."""
    return conn.execute(
        "select i.* from item i"
        " where i.status = 'active' and i.skill_set_code = %s and i.difficulty = %s"
        "   and not exists (select 1 from item_exposure x where x.item_id = i.id"
        "                   and x.child_id = %s and x.created_at > now() - make_interval(days => %s))"
        " order by i.times_used, i.item_key",
        (skill_set, difficulty, child_id, int(window_days)),
    ).fetchall()


def for_week(conn, section: str, week: str, kind: str = "practice") -> dict:
    """Build a sheet for every prescription in the section this week, plus the spares.

    Draws without replacement across the whole class so no two children share a question, and
    records what each child was shown.
    """
    tenant = conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]
    per_sheet = int(_config(conn, "assemble.items_per_sheet", 12))
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

    taken: set[str] = set()      # item ids already used by this class this week
    built, short = [], []
    for p in rx:
        pool = [r for r in _available(conn, p["skill_set_code"], p["difficulty"], p["child_id"], window)
                if r["id"] not in taken]
        if len(pool) < per_sheet:
            short.append({"roll_no": p["roll_no"], "difficulty": p["difficulty"],
                          "had": len(pool), "needed": per_sheet})
            continue
        rng = random.Random(int(hashlib.sha1(f"{p['child_id']}|{week}|{kind}".encode()).hexdigest(), 16) % (2**32))
        chosen = rng.sample(pool, per_sheet)
        taken.update(r["id"] for r in chosen)
        built.append(_store(conn, tenant, p, chosen, week, kind))

    spares = []
    for difficulty in sorted({p["difficulty"] for p in rx}):
        skill_set = next(p["skill_set_code"] for p in rx if p["difficulty"] == difficulty)
        band = next(p["band"] for p in rx if p["difficulty"] == difficulty)
        for n in range(spares_each):
            pool = [r for r in conn.execute(
                "select * from item where status = 'active' and skill_set_code = %s and difficulty = %s"
                " order by times_used, item_key", (skill_set, difficulty)).fetchall()
                if r["id"] not in taken]
            if len(pool) < per_sheet:
                break
            rng = random.Random(int(hashlib.sha1(f"spare|{difficulty}|{n}|{week}".encode()).hexdigest(), 16) % (2**32))
            chosen = rng.sample(pool, per_sheet)
            taken.update(r["id"] for r in chosen)
            spares.append(_store(conn, tenant, {"id": None, "child_id": None, "skill_set_code": skill_set,
                                                "difficulty": difficulty, "band": band, "roll_no": f"spare {n + 1}",
                                                "rule_fired": "spare"},
                                 chosen, week, kind))

    return {"sheets": built, "spares": spares, "short": short}


def _store(conn, tenant, p, items, week, kind):
    """One template (the questions and the key) and one instance (the code on the page)."""
    template = conn.execute(
        "insert into sheet_template (tenant_id, band, week, variant, item_ids, skill_set_code,"
        " difficulty, child_id, source) values (%s,%s,%s,1,%s,%s,%s,%s,'generated') returning id",
        (tenant, p["band"], week, [r["id"] for r in items], p["skill_set_code"], p["difficulty"],
         p["child_id"]),
    ).fetchone()["id"]
    qr = _qr(template, p["child_id"], week, kind)
    instance = conn.execute(
        "insert into sheet_instance (tenant_id, qr_code, sheet_template_id, child_id)"
        " values (%s,%s,%s,%s) returning id, qr_code",
        (tenant, qr, template, p["child_id"]),
    ).fetchone()
    if p["id"]:
        conn.execute("update prescription set sheet_instance_id = %s where id = %s", (instance["id"], p["id"]))
    if p["child_id"]:
        for r in items:
            conn.execute(
                "insert into item_exposure (tenant_id, child_id, item_id, week) values (%s,%s,%s,%s)"
                " on conflict (tenant_id, child_id, item_id) do nothing",
                (tenant, p["child_id"], r["id"], week))
    conn.execute("update item set times_used = times_used + 1 where id = any(%s)", ([r["id"] for r in items],))
    return {"template_id": template, "instance_id": instance["id"], "qr": instance["qr_code"],
            "child_id": p["child_id"], "roll_no": p["roll_no"], "band": p["band"],
            "difficulty": p["difficulty"], "rule": p["rule_fired"], "item_rows": items}


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

    pdfs = []
    with sync_playwright() as pw:
        for s in sheets:
            items = [item_from_row(r) for r in s["item_rows"]]
            sh = Sheet(s["qr"], s["band"], s["difficulty"], 1, week, items)
            label = f"{named.get(s['child_id'], 'Spare copy')} · {s['difficulty']} {kind}"
            key = render_sheet(sh, outdir, week_label=label, pw=pw)
            conn.execute("update sheet_template set key = %s, html_path = %s where id = %s",
                         (json.dumps(key), str(outdir / f"{s['qr']}.html"), s["template_id"]))
            conn.execute("update sheet_instance set pdf_path = %s where id = %s",
                         (str(outdir / f"{s['qr']}.pdf"), s["instance_id"]))
            pdfs.append(str(outdir / f"{s['qr']}.pdf"))
            s["pages"] = key["pages"]

    pack = outdir / f"{week}_pack.pdf"
    subprocess.run(["pdfunite", *pdfs, str(pack)], check=True)
    return {"pack": str(pack), "sheets": len(built["sheets"]), "spares": len(built["spares"]),
            "pages": sum(s["pages"] for s in sheets)}
