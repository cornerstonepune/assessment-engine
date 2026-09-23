"""N3 — the papers done before QR sheets existed, read into the same evidence generated sheets
produce (SPEC §6, "Legacy sheet"). The paper is entered once as a template; each scan is one
whole-page model call per page; marking is by lookup against the printed operands; everything
lands as a candidate for a person to confirm. A model transcribes, code marks — never the reverse.
"""

import hashlib
import json
import re
import threading
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np

from engine.adapters import llm, ocr
from engine.assess import misconceptions as M
from engine.assess import placing, tags
from engine.assess.items import Item
from engine.core import db
from engine.w3_read import profiles, reading, render_pdf
from engine.w3_read.marking import _MINUS, UNTRUSTED, mark_read, normalise_answer

PAPERS = db.REPO_ROOT / "supabase" / "seed" / "papers"
# `capture_live_content_idx` forbids two LIVE captures of one file, so on a re-read the old row must
# leave the live set BEFORE the new one is inserted — and at that moment its replacement does not
# exist yet. It points at itself for those few statements, which is non-null (so it is no longer
# live) and self-describing, and is repointed at the real replacement below.
_EXPR = re.compile(r"^\s*(\d+)\s*([+\-−–×x])\s*(\d+)\s*=?\s*$")
_SKILL_FOR_OP = {"+": "NUM.OPS.01", "-": "NUM.OPS.02"}


def parse_expr(text):
    """'348 + 27 =' → ('+', 348, 27); None when the line is not a bare two-operand sum."""
    m = _EXPR.match(text.translate(_MINUS))
    return (m.group(2), int(m.group(1)), int(m.group(3))) if m else None


def where_they_go(conn):
    """The skills, the taxonomy's cases and each rung's skills: what `rung_for` and `skill_for` read (ADR 0034)."""
    skills = conn.execute("select code, rung_code, difficulty from skill_set").fetchall()
    cases = {r["code"]: r["match"] for r in conn.execute("select code, match from taxonomy_case")}
    return (
        skills,
        cases,
        {r["code"]: r["skill_codes"] for r in conn.execute("select code, skill_codes from rung")},
    )


def rung_for(op, a, b, where):
    """The rung of the skill a bare sum practises, from its numbers alone — the one skill whose operation and
    digit shape it has (`assess/placing.py`), exactly as the bank's own questions are placed; None off them."""
    if op == "×" or (op == "-" and a < b):
        return None
    t = tags.derive(Item("", "", "", [], "", "bare_sum", False, "", {"a": a, "b": b, "op": op}, []))
    home = placing.place("bare_sum", t, *where[:2])
    return home[0]["rung_code"] if home else None


def skill_for(rung, op, rung_skills):
    """The skill an old paper's question counts on: addition's or subtraction's for a sum, else its rung's."""
    if op in _SKILL_FOR_OP:
        return _SKILL_FOR_OP[op]
    if not rung_skills.get(rung):
        raise ValueError(f"rung {rung!r} names no skill; give the item a skill")
    return rung_skills[rung][0]


# ---- the paper, entered once


def _template_item(paper, it, where):
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
        rung = it.get("rung") or rung_for(op, a, b, where)
        if rung is None:
            raise ValueError(
                f"item {it['n']}{it.get('part', '')}: {it['expr']!r} is not on the ladder; give it a rung"
            )
    else:
        answer = it.get("answer")
        predictions = M.predict_sign(answer) if answer is not None else {}
        rung = it.get("rung")
        if rung is None:
            raise ValueError(f"item {it['n']}{it.get('part', '')} has no expr and no rung")
    spec["answer"] = answer
    spec["skill"] = it.get("skill") or skill_for(rung, spec.get("op"), where[2])
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
    ids, where = [], where_they_go(conn)
    for it in paper["items"]:
        t = _template_item(paper, it, where)
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
        "select id, item_key, fmt, spec, responses from item where id = any(%s)", (list(_ids(conn, t["id"])),)
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


def render_pages(path, pages=None, long_side=0):
    """A PDF or an image → one JPEG bytes per page.

    `pages` selects pages out of a multi-page document. It does NOT apply to a photograph: a
    Grade 3 sitting is one JPEG per page, so `--pages 2` on one of those means "this file is page 2
    of the paper", which `import_scan` uses to look up the right slots. Filtering a one-image file
    by that number returned an empty list and read nothing at all.

    `long_side` is for showing a page (`_rendered`), never for reading one.
    """
    path = Path(path)
    photo = path.suffix.lower() in (".jpg", ".jpeg", ".png")
    out = [cv2.imread(str(path))] if photo else render_pdf.render(path, long_side=long_side)
    if pages and not photo:
        out = [out[i - 1] for i in pages if 0 < i <= len(out)]
    return [_jpeg(_fit(im, long_side)) for im in out]


def _fit(img, long_side):
    """A photograph shrunk to `long_side`; a PDF page arrives already drawn at it."""
    h, w = img.shape[:2]
    if not long_side or max(h, w) <= long_side:
        return img
    scale = long_side / max(h, w)
    return cv2.resize(img, (round(w * scale), round(h * scale)), interpolation=cv2.INTER_AREA)


# The longest side a page is shown at: about 200 dpi on A4, more than the 150 it is read at, so a
# person never sees fewer pixels than the reader did. A WhatsApp "scan" drawn at 150 dpi is
# 5490 x 8138 — 134 MB decoded, for a picture shown 400 px wide — and the approval page asks for a
# dozen of them at once: 3.3 GB on a 2 GB server, which killed the engine (2026-09-21).
SCREEN_PX = 2400
# ponytail: one lock for every paper, so two people opening two different papers at the same
# moment wait about a second for each other's first drawing; a lock per paper if that is ever felt.
_drawing = threading.Lock()


@lru_cache(maxsize=8)
def _rendered(path, mtime):
    """Every page of a file as JPEG bytes at the size a screen shows it, remembered. The approval
    screen asks for one crop per answer — eighteen requests for one page — and re-rendering a PDF
    each time would make a screen a teacher has to wait for. Keyed on the file's mtime so a
    re-photographed page is not stale."""
    del mtime
    return render_pages(path, long_side=SCREEN_PX)


def page_crop(path, page_no, box=None, pad=0.01):
    """One page of a scan as JPEG bytes, or the patch of it an answer was read from.

    `box` is (left, top, right, bottom) as fractions of the page — `item_result.raw_read`'s own
    `box`, so what a person is shown is exactly the region the reading came from, not an
    approximation of it. A file holding a single image IS one page however the paper numbers it:
    a Grade 3 sitting is one photograph per page, so its second page is a second file.
    """
    with _drawing:  # a burst of requests for one paper draws it once; the rest find it remembered
        images = _rendered(str(path), Path(path).stat().st_mtime)
    return crop(images[min(max(page_no, 1), len(images)) - 1], box, pad)


def crop(jpeg, box=None, pad=0.01):
    """The patch of a page image a box names, as JPEG bytes — or the whole page where there is no
    box, or where the box is too small to be worth looking at on its own."""
    if not box:
        return jpeg
    img = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)
    h, w = img.shape[:2]
    left, top, right, bottom = box
    x0 = max(0, int((left - pad) * w))
    y0 = max(0, int((top - pad) * h))
    x1 = min(w, int((right + pad) * w))
    y1 = min(h, int((bottom + pad) * h))
    if x1 - x0 < 8 or y1 - y0 < 8:  # a region too small to see is more use whole than cropped
        return jpeg
    return _jpeg(img[y0:y1, x0:x1])


@lru_cache(maxsize=2)
def _sharp_page(path, mtime, page_no, dpi):
    """One page at the resolution a doubtful answer is looked at again in, as JPEG bytes.

    A photograph is already at its own resolution and there is no more to render — the gain there
    is that the answer fills the frame instead of being one word on a whole page. A PDF is a
    different matter: it was read at 150 dpi and can be drawn again at any size.

    Cached because a page holds many doubtful answers and rendering an A4 page at 500 dpi is not
    free; JPEG bytes rather than the array, so the cache is megabytes and not hundreds of them.
    """
    del mtime
    p = Path(path)
    if p.suffix.lower() in (".jpg", ".jpeg", ".png"):
        return _jpeg(cv2.imread(str(p)))
    pages = render_pdf.render(p, dpi, render_pdf.MAX_PIXELS)
    return _jpeg(pages[min(max(page_no, 1), len(pages)) - 1])


def second_look(path, page_no, fraction, cfg, cli):
    """→ a `reread(box)` for `ocr.answers_for`, or None when the row turns the second look off.

    The big render happens on the first doubtful answer of a page and not before: a page the engine
    reads cleanly costs nothing extra, and a page with no doubts never opens the file twice.
    """
    if not cfg.get("reread_dpi"):
        return None
    sharp = []

    def reread(box):
        if not sharp:
            jpeg = _sharp_page(str(path), Path(path).stat().st_mtime, page_no, int(cfg["reread_dpi"]))
            # The same page the engine read, masked the same way: the name band stays painted out
            # (rule 6) and the educator's red ink stays inpainted, or a crop would hand back the
            # very reading those two rules exist to prevent.
            sharp.append(ocr.mask_red_pen(mask_name_band(jpeg, fraction), cfg))
        return ocr.read(crop(sharp[0], box, pad=0.0), cli)

    return reread


def masked_image(jpeg, fraction):
    """The masked page as an array, for cutting bands from without a re-encode per band."""
    img = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)
    if fraction:
        img[: int(img.shape[0] * fraction), :] = 255
    return img


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


def symbolic_slots(by_key):
    """The slots whose answer is not a number: "456 [ ] 465" wants "<", not a value.

    The paper row already knows — it is the answer the question was entered with — so the reader is
    told rather than left to infer it from a question's wording.
    """
    return {
        k
        for k, it in by_key.items()
        if it["spec"].get("answer") is not None
        and not re.fullmatch(r"-?\d+", str(it["spec"]["answer"]).strip())
    }


def slot_list(by_key, page_no):
    """The answer slots printed on one page, as the reader is shown them.

    The paper already holds every printed question — asking the model to transcribe them back was
    both redundant and harmful: writing "348 + 27 =" before reaching the child's answer primed it to
    compute 375, and it returned the right answer in place of the child's wrong one about a fifth of
    the time. Handing it the slots instead also ends the missing-row problem, because a slot it
    cannot find must come back as `not_found` rather than simply never appearing.
    """
    on_page = [(k, it) for k, it in by_key.items() if it["spec"].get("page", 1) == page_no]
    on_page.sort(key=lambda kv: (int("".join(c for c in kv[0] if c.isdigit()) or 0), kv[0]))
    return "\n".join(f"{k:<4} {_locator(it['spec']['question'])}" for k, it in on_page)


def _locator(question):
    """Enough of a printed question to FIND its answer on the page.

    Masking the digits was tried, to stop the reader computing the answer from its own instructions,
    and measured WORSE — 51.8% against 63.0%. Removing the numbers takes away what locates a slot
    on the page without taking away the arithmetic, which is still printed on the page the reader is
    looking at. The failure was never about what the prompt contained: a vision model that knows
    arithmetic fills a gap in faint pencil with the answer it can compute, and no phrasing prevents
    that. See ADR 0019 — the transcription layer moves to an OCR engine that cannot do sums.
    """
    return question[:90]


# A whole page goes to the model as roughly 1568px on its long edge, so a handwritten "397" lands in
# about 40x25 pixels. Measured on a real page: asked for six answers on the whole page the reader got
# two right, and asked for the same six on tight crops it got four — and both it gained were cases
# where it had previously returned the arithmetically CORRECT answer instead of the child's wrong
# one. It was not disobeying the instruction to transcribe; it could not see the pencil, and a
# maths-shaped prior filled the gap. Bands give each digit its own share of the pixel budget.
#
# They overlap so that no answer falls on a seam, which means most answers are read twice — and two
# bands disagreeing about one answer is a *measured* doubt, worth far more than a model's opinion of
# its own confidence. That doubt goes to a person instead of being guessed at, which is what the
# silent-error bar is for.
BANDS = ((0.00, 0.42), (0.30, 0.72), (0.58, 1.00))


def read_page_in_bands(conn, image, slots, bands=BANDS):
    """One page → {slot: reading}, read once per band and merged. Returns (readings, disagreements)."""
    h = image.shape[0]
    seen = {}
    for top, bottom in bands:
        crop = image[int(h * top) : int(h * bottom)]
        got = llm.generate(conn, "legacy_extract", {"slots": slots}, images=[_jpeg(crop)])
        for r in got["items"]:
            seen.setdefault(r["slot"], []).append(r)
    return _merge_bands(seen)


# What one band knows about a slot, strongest first. `not_found` is the weakest by a distance: it
# means "not in the part of the page I was shown", which every band says about most of the page. It
# must never outrank a band that could actually see the slot and found it empty — letting it do so
# turned two genuinely blank answers into `not_found` and cost four correct readings.
_STATE_RANK = {"written": 0, "blank": 1, "illegible": 2, "not_visible": 3, "not_found": 4}


def _merge_bands(seen):
    """Readings of one slot from several bands → one reading, or a disagreement a person settles."""
    out, disagreements = {}, []
    for slot, reads in seen.items():
        best = min(_STATE_RANK[r["answer_state"]] for r in reads)
        agree = [r for r in reads if _STATE_RANK[r["answer_state"]] == best]
        if best == 0:  # at least one band read handwriting here
            values = {normalise_answer(r["child_answer"]) for r in agree}
            if len(values) > 1:
                # Two bands saw the same slot and read it differently. That is measured doubt, and
                # it is worth more than any confidence a model reports about itself — so it goes to
                # a person rather than being resolved by picking one.
                disagreements.append({"slot": slot, "values": sorted(values)})
                out[slot] = {**agree[0], "child_answer": "", "answer_state": "illegible"}
                continue
        out[slot] = agree[0]
    return out, disagreements


def _page_resolution(summary, page_no, out):
    """The reader's own account of the page (ADR 0018) → one line for a person, and every thing it
    could not settle collected for the approval queue. `needs` is what code routes on: a page that
    says `nothing` is a complete answer, not a failure, and a cover page saying so is the difference
    between an honest empty list and an invented question."""
    res = out["resolution"]
    for u in res["unresolved"]:
        summary.setdefault("unresolved", []).append({**u, "page": page_no})
    unmet = [u for u in res["unresolved"] if u["needs"] != "nothing"]
    tail = f" — {len(unmet)} needing attention" if unmet else ""
    return f"{res['status']}: {res['saw']}{tail}"


def worked_on(conn, capture_id):
    """How many answers on this capture a person has signed off or corrected.

    A re-read would supersede the capture that work hangs from, and every screen and the graph read
    only live captures — so a better reader would quietly undo a teacher's work. The first version of
    this guard counted sign-offs only, and a re-read took six of Nimish's corrections on a paper he
    had not yet signed off. What a person has checked, a person has checked: it is not read again.
    """
    return conn.execute(
        "select (select count(*) from item_result where capture_id = %s and state = 'confirmed')"
        " + (select count(*) from read_correction where capture_id = %s) as n",
        (capture_id, capture_id),
    ).fetchone()["n"]


def import_scan(
    conn, path, paper_code, child_id, actor, pages=None, masks=None, narrative=False, again=False
):
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

    stale_id = None
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
    signed = existing and worked_on(conn, existing["id"])
    if signed and again:
        return {
            "capture_id": existing["id"],
            "pages": existing["pages"],
            "results": [],
            "unmatched": [],
            "notes": [f"a person has worked on this paper ({signed} answers): not read again"],
            "already": True,
            "already_results": signed,
        }
    if existing and again:
        # The scan is unchanged but the PAPER is not — `G2-CAM-A` went from 24 answer slots to the
        # 27 its page holds, and three answers per child had nowhere to land. Idempotency keys on
        # the file alone, so it reported "nothing to do" on a reading that was three answers short.
        # `engine.w3_read.stale` finds these; this re-reads one. The old capture is superseded, never
        # deleted (rule 4) — a teacher may have confirmed rows on it and that history stays.
        stale_id = existing["id"]
        existing = None
        conn.execute("update capture set superseded_by = id where id = %s", (stale_id,))
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

    if stale_id:  # point the placeholder at the reading that actually replaced it
        conn.execute("update capture set superseded_by = %s where id = %s", (capture, stale_id))

    summary = {"capture_id": capture, "pages": len(images), "results": [], "unmatched": [], "notes": []}
    try:
        cli = ocr.client()
        trust = profiles.kind_trust(conn)
        scan = {
            "path": path,
            "paper_code": paper_code,
            "paper": paper,
            "by_key": by_key,
            "page_numbers": page_numbers,
            "images": images,
            "masks": masks,
        }
        for pg in reading.read_pages(conn, scan, cli, child_id):
            page_no, jpeg, readings = pg["page_no"], pg["jpeg"], pg["readings"]
            summary["notes"].append(pg["note"])
            if readings is None:
                continue
            for key, read in readings.items():
                it = by_key.get(key)
                if not it or it["spec"].get("page", 1) != page_no:
                    summary["unmatched"].append(key)
                    continue
                status, codes, working, read = mark_read(
                    it["spec"], it["responses"][0], read, trust.get(it["fmt"], UNTRUSTED)
                )
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
                        "confidence": read.get("confidence"),
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
