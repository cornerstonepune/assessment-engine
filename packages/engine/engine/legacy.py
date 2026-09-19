"""N3 — the papers done before QR sheets existed, read into the same evidence generated sheets
produce (SPEC §6, "Legacy sheet"). The paper is entered once as a template; each scan is one
whole-page model call per page; marking is by lookup against the printed operands; everything
lands as a candidate for a person to confirm. A model transcribes, code marks — never the reverse.
"""

import hashlib
import json
import re
from pathlib import Path

import cv2
import numpy as np

from engine import db, render_pdf
from engine.adapters import llm
from engine.assess import misconceptions as M
from engine.assess import tags
from engine.assess.ladder import RUNGS

PAPERS = db.REPO_ROOT / "supabase" / "seed" / "papers"
_EXPR = re.compile(r"^\s*(\d+)\s*([+\-−–×x])\s*(\d+)\s*=?\s*$")
_MINUS = str.maketrans({"−": "-", "–": "-", "x": "×"})
_SKILL_FOR_OP = {"+": "NUM.OPS.01", "-": "NUM.OPS.02"}


def parse_expr(text):
    """'348 + 27 =' → ('+', 348, 27); None when the line is not a bare two-operand sum."""
    m = _EXPR.match(text.translate(_MINUS))
    return (m.group(2), int(m.group(1)), int(m.group(3))) if m else None


def rung_for(op, a, b):
    """Which ladder rung a bare sum exercises, from its shape alone. Mirrors the taxonomy: digits
    and where the regrouping falls, not the grade the paper was set for."""
    width = max(len(str(a)), len(str(b)))
    cols = tags._regroup_columns(op, a, b)
    if op == "×":
        return None  # off the addition/subtraction ladder (manifest.md: no multiplication rung yet)
    if width <= 2:
        return "R4" if not cols else ("R5" if op == "+" else "R6")
    if width == 3:
        if op == "-" and tags._pattern(op, a, b, cols) == "ACROSS_ZERO":
            return "R10"
        return "R9" if cols else "R4"  # columns without regrouping is R4's idea at any width
    return "R12"


def skill_for(rung, op=None):
    skills = RUNGS[rung]["skills"]
    return _SKILL_FOR_OP.get(op) if op in _SKILL_FOR_OP and _SKILL_FOR_OP[op] in skills else skills[0]


def normalise_answer(text):
    """What the child wrote, as a number string: '1,264' → '1264', '43 apples' → '43',
    'ans=43' → '43', '' stays ''. A read with digits tangled in other marks ('3?5') is returned
    as-is so it is marked unreadable rather than guessed at."""
    t = text.translate(_MINUS).replace(",", "").strip().rstrip(".")
    m = re.fullmatch(r"[^\d-]*(-?\d+)[A-Za-z₹.\s]*", t)
    return m.group(1) if m else t


# ---- the paper, entered once


def _template_item(paper, it):
    """One printed question as an item row: operands, the right answer, and — for a bare sum —
    the wrong answers each misconception would produce, so marking is a lookup."""
    kind = it.get("kind", "bare")
    parsed = parse_expr(it["expr"]) if it.get("expr") else None
    spec = {"kind": kind, "expr": it.get("expr"), "question": it["question"]}
    predictions = {}
    if parsed:
        op, a, b = parsed
        spec |= {"op": op, "a": a, "b": b}
        answer = it.get("answer", M.compute(op, a, b))
        predictions = M.predict(op, a, b)
        rung = it.get("rung") or rung_for(op, a, b)
        if rung is None:
            raise ValueError(
                f"item {it['n']}{it.get('part', '')}: {it['expr']!r} is not on the ladder; give it a rung"
            )
    else:
        answer = it.get("answer")
        rung = it.get("rung")
        if rung is None:
            raise ValueError(f"item {it['n']}{it.get('part', '')} has no expr and no rung")
    spec["answer"] = answer
    spec["skill"] = it.get("skill") or skill_for(rung, spec.get("op"))
    spec["page"] = it.get("page", 1)
    signal = {"bare": "Procedural", "word": "Application", "missing": "Conceptual", "text": "Stretch"}[kind]
    return {
        "item_key": f"legacy/{paper['code']}/{it['n']}{it.get('part', '')}",
        "rung": rung,
        "skill": spec["skill"],
        "signal": signal,
        "fmt": f"legacy_{kind}",
        "stem": it["question"],
        "spec": spec,
        "responses": [
            {"rid": "a", "answer": None if answer is None else str(answer), "misconceptions": predictions}
        ],
    }


def load_paper(conn, path):
    """Upsert a paper definition: one sheet_template(source=legacy) and one item per printed
    question. Re-running with a corrected file updates the rows. Returns the template id."""
    paper = json.loads(Path(path).read_text())
    tenant = conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]
    ids = []
    for it in paper["items"]:
        t = _template_item(paper, it)
        row = conn.execute(
            "insert into item (tenant_id, item_key, template, rung_code, skill_codes, signal, fmt, stem,"
            " spec, responses, source, status)"
            " values (%s,%s,'legacy',%s,%s,%s,%s,%s,%s,%s,'legacy','active')"
            " on conflict (tenant_id, item_key) do update set rung_code = excluded.rung_code,"
            " skill_codes = excluded.skill_codes, signal = excluded.signal, fmt = excluded.fmt,"
            " stem = excluded.stem, spec = excluded.spec, responses = excluded.responses, updated_at = now()"
            " returning id",
            (
                tenant,
                t["item_key"],
                t["rung"],
                [t["skill"]],
                t["signal"],
                t["fmt"],
                t["stem"],
                json.dumps(t["spec"]),
                json.dumps(t["responses"]),
            ),
        ).fetchone()
        ids.append(row["id"])
    existing = conn.execute(
        "select id from sheet_template where tenant_id = %s and source = 'legacy' and batch_id = %s",
        (tenant, paper["code"]),
    ).fetchone()
    if existing:
        conn.execute(
            "update sheet_template set band = %s, week = %s, item_ids = %s, key = %s, updated_at = now()"
            " where id = %s",
            (paper["band"], paper["week"], ids, json.dumps(paper), existing["id"]),
        )
        return existing["id"]
    return conn.execute(
        "insert into sheet_template (tenant_id, band, week, variant, batch_id, item_ids, key, source)"
        " values (%s,%s,%s,1,%s,%s,%s,'legacy') returning id",
        (tenant, paper["band"], paper["week"], paper["code"], ids, json.dumps(paper)),
    ).fetchone()["id"]


def paper_rows(conn, code):
    t = conn.execute(
        "select id, tenant_id, key from sheet_template where source = 'legacy' and batch_id = %s", (code,)
    ).fetchone()
    if not t:
        raise ValueError(f"no paper {code!r}; run `engine legacy paper` first")
    items = conn.execute(
        "select id, item_key, spec, responses from item where id = any(%s)", (list(_ids(conn, t["id"])),)
    ).fetchall()
    by_key = {}
    for it in items:
        n_part = it["item_key"].rsplit("/", 1)[1]
        by_key[n_part] = it
    return t, by_key


def _ids(conn, template_id):
    return conn.execute("select item_ids from sheet_template where id = %s", (template_id,)).fetchone()[
        "item_ids"
    ]


# ---- the scan


def render_pages(path, pages=None):
    """A PDF or an image → one JPEG bytes per page."""
    path = Path(path)
    out = (
        [cv2.imread(str(path))]
        if path.suffix.lower() in (".jpg", ".jpeg", ".png")
        else render_pdf.render(path)
    )
    if pages:
        out = [out[i - 1] for i in pages if 0 < i <= len(out)]
    return [_jpeg(im) for im in out]


def mask_name_band(jpeg, fraction):
    """Paint over the top band where the printed name sits (rule 6: prompts receive images, not
    names). The fraction is per paper, per page, and can be overridden per scan."""
    if not fraction:
        return jpeg
    img = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)
    h = img.shape[0]
    img[: int(h * fraction), :] = 255
    return _jpeg(img)


def _jpeg(img):
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 82])
    if not ok:
        raise RuntimeError("could not encode page")
    return buf.tobytes()


# ---- marking, by lookup


def mark(spec, response, read):
    """→ (status, misconception codes, working_shown). Blank, wrong and wrong-with-working stay
    three signals (rule 5): status carries the first two, working_shown the third."""
    working = (
        "partial" if read.get("working_summary") else "none"
    )  # ponytail: the page call cannot tell partial from full
    answer = normalise_answer(read.get("child_answer", ""))
    if spec["kind"] == "text":
        return ("blank" if not read.get("attempted") and not answer else "needs_teacher"), [], working
    if not answer:
        return ("needs_teacher" if read.get("attempted") else "blank"), [], working
    if not re.fullmatch(r"-?\d+", answer):
        return "unreadable", [], working
    n = int(answer)
    want = response.get("answer")
    if want is not None and n == int(want):
        return "correct", [], working
    codes = sorted(code for code, wrong in response.get("misconceptions", {}).items() if wrong == n)
    return "wrong", codes, working


def import_scan(conn, path, paper_code, child_id, actor, pages=None, masks=None, narrative=False):
    """One scan of one child's paper → capture, item_result rows (candidate), and optionally a
    narrative_observation. Returns a summary a person can read before confirming.

    Idempotent on the file's content: reading the same scan for the same child again returns the
    existing capture rather than a second one — the September batch's double count (HANDOFF.md)
    was two `legacy import` runs over the same file, each making its own candidates. A prior
    attempt that errored retries into that same row instead of leaving a third."""
    template, by_key = paper_rows(conn, paper_code)
    paper = template["key"]
    tenant = template["tenant_id"]
    page_specs = {p["n"]: p for p in paper.get("pages", [{"n": 1}])}

    qr = f"LEGACY-{paper_code}-{str(child_id)[:8]}"
    instance = conn.execute(
        "insert into sheet_instance (tenant_id, qr_code, sheet_template_id, child_id, print_status)"
        " values (%s,%s,%s,%s,'returned') on conflict (tenant_id, qr_code) do update set updated_at = now()"
        " returning id",
        (tenant, qr, template["id"], child_id),
    ).fetchone()["id"]

    file_sha256 = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    existing = conn.execute(
        "select id, status, pages from capture where sheet_instance_id = %s and file_sha256 = %s"
        " and superseded_by is null",
        (instance, file_sha256),
    ).fetchone()
    if existing and existing["status"] == "processed":
        n = conn.execute(
            "select count(*) as n from item_result where capture_id = %s", (existing["id"],)
        ).fetchone()["n"]
        return {
            "capture_id": existing["id"],
            "pages": existing["pages"],
            "results": [],
            "unmatched": [],
            "notes": [],
            "already": True,
            "already_results": n,
        }

    images = render_pages(path, pages)
    page_numbers = pages or sorted(page_specs)[: len(images)]
    rel = str(Path(path).resolve()).replace(str(Path.home()), "~")
    if existing:  # a previous attempt on this exact file errored; retry into that row, not a new one
        capture = existing["id"]
        conn.execute(
            "update capture set pages = %s, status = 'new', error = null where id = %s",
            (len(images), capture),
        )
    else:
        capture = conn.execute(
            "insert into capture (tenant_id, path, pages, sheet_instance_id, status, qr_read, file_sha256)"
            " values (%s,%s,%s,%s,'new',%s,%s) returning id",
            (tenant, rel, len(images), instance, qr, file_sha256),
        ).fetchone()["id"]

    summary = {"capture_id": capture, "pages": len(images), "results": [], "unmatched": [], "notes": []}
    try:
        for page_no, jpeg in zip(page_numbers, images):
            fraction = (masks or {}).get(page_no, page_specs.get(page_no, {}).get("mask", 0))
            jpeg = mask_name_band(jpeg, fraction)
            expected = sum(1 for it in by_key.values() if it["spec"].get("page", 1) == page_no)
            out = llm.generate(conn, "legacy_extract", {"expected": str(expected)}, images=[jpeg])
            if out.get("page_note"):
                summary["notes"].append(f"p{page_no}: {out['page_note']}")
            for read in out["items"]:
                key = f"{read['n']}{read.get('part', '')}"
                it = by_key.get(key)
                if not it or it["spec"].get("page", 1) != page_no:
                    summary["unmatched"].append(key)
                    continue
                status, codes, working = mark(it["spec"], it["responses"][0], read)
                conn.execute(
                    "insert into item_result (tenant_id, capture_id, item_id, rid, raw_read, status,"
                    " misconception_codes, working_shown, state)"
                    " values (%s,%s,%s,'a',%s,%s,%s,%s,'candidate')"
                    " on conflict (capture_id, item_id, rid) do update set raw_read = excluded.raw_read,"
                    " status = excluded.status, misconception_codes = excluded.misconception_codes,"
                    " working_shown = excluded.working_shown, updated_at = now()",
                    (tenant, capture, it["id"], json.dumps(read), status, codes, working),
                )
                summary["results"].append(
                    {
                        "item": key,
                        "question": it["spec"]["question"],
                        "read": read.get("child_answer", ""),
                        "status": status,
                        "codes": codes,
                        "working": working,
                    }
                )
            if narrative:
                obs = llm.generate(conn, "read_page", {}, images=[jpeg])
                conn.execute(
                    "insert into narrative_observation (tenant_id, capture_id, text, signals, prompt_version)"
                    " values (%s,%s,%s,%s,(select version from prompt where purpose = 'read_page' and active))",
                    (tenant, capture, obs["narrative"], json.dumps(obs["signals"])),
                )
        conn.execute("update capture set status = 'processed' where id = %s", (capture,))
    except llm.LLMError as e:
        conn.execute("update capture set status = 'error', error = %s where id = %s", (str(e), capture))
        raise
    conn.execute(
        "insert into access_log (tenant_id, actor, child_id, action) values (%s,%s,%s,'legacy_import')",
        (tenant, actor, child_id),
    )
    return summary


def dedupe(conn):
    """Fixes the September batch's double (and triple) import: backfills file_sha256 on captures
    that predate the column, then supersedes every live capture but the best one per (sheet, file)
    pair. Best is processed over error, then most item_result rows, then latest — never deleted
    (rule 4); a superseded row's answers simply stop being read (graph_functions migration).

    Every row's hash is computed in Python before any write, and a voided row's file_sha256 and
    superseded_by land in one statement — never two live rows sharing a hash across separate
    statements, which is exactly what capture_live_content_idx forbids.
    Returns (backfilled, voided). Safe to run again: nothing left to backfill or void is a no-op."""
    rows = conn.execute(
        "select c.id, c.path, c.file_sha256, c.status, c.created_at, c.sheet_instance_id,"
        " (select count(*) from item_result where capture_id = c.id) as n"
        " from capture c where c.superseded_by is null"
    ).fetchall()

    hashed = []
    for r in rows:
        sha, was_missing = r["file_sha256"], r["file_sha256"] is None
        if was_missing:
            p = Path(r["path"]).expanduser()
            if not p.exists():
                continue  # can't hash what isn't there; leave it live and unmatched
            sha = hashlib.sha256(p.read_bytes()).hexdigest()
        hashed.append({**r, "file_sha256": sha, "was_missing": was_missing})

    groups: dict[tuple, list] = {}
    for r in hashed:
        groups.setdefault((r["sheet_instance_id"], r["file_sha256"]), []).append(r)

    backfilled = voided = 0
    for members in groups.values():
        members.sort(key=lambda r: (r["status"] == "processed", r["n"], r["created_at"]), reverse=True)
        keeper, rest = members[0], members[1:]
        if keeper["was_missing"]:
            conn.execute(
                "update capture set file_sha256 = %s where id = %s", (keeper["file_sha256"], keeper["id"])
            )
            backfilled += 1
        for r in rest:
            conn.execute(
                "update capture set file_sha256 = %s, superseded_by = %s where id = %s",
                (r["file_sha256"], keeper["id"], r["id"]),
            )
            backfilled += r["was_missing"]
            voided += 1
    return backfilled, voided


def remark(conn, child_id):
    """Mark every candidate again from what was read, without asking the model again — for when
    the marking rule improves after a page was read. Returns how many rows changed."""
    rows = conn.execute(
        "select r.id, r.raw_read, r.status, r.misconception_codes, r.working_shown, i.spec, i.responses"
        " from item_result r join item i on i.id = r.item_id"
        " join capture c on c.id = r.capture_id join sheet_instance si on si.id = c.sheet_instance_id"
        " where si.child_id = %s and r.state = 'candidate' and r.raw_read is not null",
        (child_id,),
    ).fetchall()
    changed = 0
    for r in rows:
        status, codes, working = mark(r["spec"], r["responses"][0], json.loads(r["raw_read"]))
        if (status, codes, working) != (r["status"], list(r["misconception_codes"]), r["working_shown"]):
            conn.execute(
                "update item_result set status = %s, misconception_codes = %s, working_shown = %s"
                " where id = %s",
                (status, codes, working, r["id"]),
            )
            changed += 1
    return changed


def confirm(conn, child_id, by):
    return conn.execute("select confirm_results(%s, %s) as n", (child_id, by)).fetchone()["n"]


def child_map(conn, child_id):
    """The rows the Growth screen shows: every rung with evidence, its state, and the next step
    per skill set — computed by the same database functions the web app calls."""
    states = conn.execute(
        "select s.rung_code, s.skill_code, s.state, s.n_events, s.n_correct, s.repeating_misconception,"
        " r.descriptor, r.ladder_order from child_skill_state s join rung r on r.code = s.rung_code"
        " where s.child_id = %s order by r.ladder_order nulls last",
        (child_id,),
    ).fetchall()
    nxt = conn.execute(
        "select s.code, s.rung_code, n.difficulty, n.rule, n.targets from skill_set s,"
        " lateral next_difficulty(%s, s.code) n order by s.code",
        (child_id,),
    ).fetchall()
    pending = conn.execute(
        "select count(*) as n from item_result r join capture c on c.id = r.capture_id"
        " join sheet_instance si on si.id = c.sheet_instance_id"
        " where si.child_id = %s and r.state = 'candidate' and c.superseded_by is null",
        (child_id,),
    ).fetchone()["n"]
    return {"states": states, "next": nxt, "pending": pending}
