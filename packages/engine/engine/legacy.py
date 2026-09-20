"""N3 — the papers done before QR sheets existed, read into the same evidence generated sheets
produce (SPEC §6, "Legacy sheet"). The paper is entered once as a template; each scan is one
whole-page model call per page; marking is by lookup against the printed operands; everything
lands as a candidate for a person to confirm. A model transcribes, code marks — never the reverse.
"""

import hashlib
import json
import re
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np

from engine import db, render_pdf
from engine.adapters import llm, ocr
from engine.assess import misconceptions as M
from engine.assess import tags
from engine.assess.ladder import RUNGS

PAPERS = db.REPO_ROOT / "supabase" / "seed" / "papers"
# `capture_live_content_idx` forbids two LIVE captures of one file, so on a re-read the old row must
# leave the live set BEFORE the new one is inserted — and at that moment its replacement does not
# exist yet. It points at itself for those few statements, which is non-null (so it is no longer
# live) and self-describing, and is repointed at the real replacement below.
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
    if a < 10 and b < 10:
        # A one-digit sum is not a two-digit column sum with a blank in front of it. The shape rule
        # below reads "4 + 3" as width 2 without regrouping and files it under R4, which would tell
        # the engine a child who cannot add within 10 has failed at place-value columns. The
        # Cambridge Level D paper is entirely these, and it is the paper the weakest child sat.
        return ("R1" if a + b <= 10 else "R2") if op == "+" else "R3"
    if width <= 2:
        return "R4" if not cols else ("R5" if op == "+" else "R6")
    if width == 3:
        if op == "-" and tags._pattern(op, a, b, cols) == "ACROSS_ZERO":
            return "R10"
        return "R9" if cols else "R4"  # columns without regrouping is R4's idea at any width
    return "R12"


def skill_for(rung, op=None):
    if rung not in RUNGS:
        # A rung added as rows and never as Python — M1, multiplication (W1 gate 3). This module
        # maps the addition/subtraction ladder, so a paper on one of those rungs names its own
        # skill rather than having one invented here.
        raise ValueError(f"rung {rung!r} is off the addition/subtraction ladder; give the item a skill")
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
    """A PDF or an image → one JPEG bytes per page.

    `pages` selects pages out of a multi-page document. It does NOT apply to a photograph: a
    Grade 3 sitting is one JPEG per page, so `--pages 2` on one of those means "this file is page 2
    of the paper", which `import_scan` uses to look up the right slots. Filtering a one-image file
    by that number returned an empty list and read nothing at all.
    """
    path = Path(path)
    photo = path.suffix.lower() in (".jpg", ".jpeg", ".png")
    out = [cv2.imread(str(path))] if photo else render_pdf.render(path)
    if pages and not photo:
        out = [out[i - 1] for i in pages if 0 < i <= len(out)]
    return [_jpeg(im) for im in out]


@lru_cache(maxsize=8)
def _rendered(path, mtime):
    """Every page of a file as JPEG bytes, remembered. The approval screen asks for one crop per
    answer — eighteen requests for one page — and re-rendering a PDF each time would make a screen
    a teacher has to wait for. Keyed on the file's mtime so a re-photographed page is not stale."""
    del mtime
    return render_pages(path)


def page_crop(path, page_no, box=None, pad=0.01):
    """One page of a scan as JPEG bytes, or the patch of it an answer was read from.

    `box` is (left, top, right, bottom) as fractions of the page — `item_result.raw_read`'s own
    `box`, so what a person is shown is exactly the region the reading came from, not an
    approximation of it. A file holding a single image IS one page however the paper numbers it:
    a Grade 3 sitting is one photograph per page, so its second page is a second file.
    """
    images = _rendered(str(path), Path(path).stat().st_mtime)
    jpeg = images[min(max(page_no, 1), len(images)) - 1]
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


def mark(spec, response, read):
    """→ (status, misconception codes, working_shown). Blank, wrong and wrong-with-working stay
    three signals (rule 5): status carries the first two, working_shown the third.

    `answer_state` (legacy_extract v3, ADR 0018) is the reader saying which of four different things
    it saw, rather than the caller inferring it from an empty string. v2 returned `attempted` and an
    empty `child_answer` for both "wrote nothing" and "wrote something I cannot read" — the exact
    collapse rule 5 forbids. `not_visible` is its own case because the SOF pages carry an educator's
    tick over a rubbed-out pencil mark: the outcome is knowable, the child's answer is not, and
    working backwards from the tick would invent an answer out of an adult's opinion of it.
    """
    working = read.get("working_shown") or ("partial" if read.get("working_summary") else "none")
    answer = normalise_answer(read.get("child_answer", ""))
    state = read.get("answer_state")
    if state == "blank":
        return "blank", [], working
    if state == "illegible":
        return "unreadable", [], working
    if state == "not_visible":
        return "needs_teacher", [], working
    if spec["kind"] == "text":
        return ("blank" if state == "blank" and not answer else "needs_teacher"), [], working
    if not answer:
        return "needs_teacher", [], working
    if not re.fullmatch(r"-?\d+", answer):
        return "unreadable", [], working
    n = int(answer)
    want = response.get("answer")
    if want is not None and not re.fullmatch(r"-?\d+", str(want)):
        # The paper asks for something that is not a number — "456 [ ] 465" wants < — and the
        # child wrote digits. Code cannot rule on that, and int() on the expected answer would
        # crash the whole import, so it goes to a person exactly as an unreadable answer does.
        return "needs_teacher", [], working
    if want is not None and n == int(want):
        return "correct", [], working
    codes = sorted(code for code, wrong in response.get("misconceptions", {}).items() if wrong == n)
    return "wrong", codes, working


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
    if existing and again:
        # The scan is unchanged but the PAPER is not — `G2-CAM-A` went from 24 answer slots to the
        # 27 its page holds, and three answers per child had nowhere to land. Idempotency keys on
        # the file alone, so it reported "nothing to do" on a reading that was three answers short.
        # `engine.stale` finds these; this re-reads one. The old capture is superseded, never
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
        cfg = ocr.settings(conn)
        cli = ocr.client()
        for page_no, jpeg in zip(page_numbers, images):
            fraction = (masks or {}).get(page_no, page_specs.get(page_no, {}).get("mask", 0))
            jpeg = mask_name_band(jpeg, fraction)
            questions = {
                k: it["spec"]["question"] for k, it in by_key.items() if it["spec"].get("page", 1) == page_no
            }
            if not questions:
                summary["notes"].append(f"p{page_no}: no answers printed on this page")
                continue
            # Textract, not a model: what reads a child's handwriting must not know arithmetic,
            # because a model that does fills faint pencil with the answer it can compute (ADR 0019).
            # Measured on 45 hand-read responses: 80% exactly right with ZERO wrong readings the
            # engine stood behind, against 55-63% with about seven of them.
            # The paper says where its answers live (rule 1): only a paper that prints a box per
            # answer hands the reader its boxes. On an underline paper a stray rectangle is not a field.
            boxes = ocr.printed_boxes(jpeg, cfg) if paper.get("fields") == "boxes" else ()
            readings = ocr.answers_for(ocr.read(jpeg, cli), questions, cfg, symbolic_slots(by_key), boxes)
            flagged = sum(1 for r in readings.values() if r["answer_state"] != "written")
            summary["notes"].append(f"p{page_no}: {len(readings)} answers read, {flagged} for a person")
            for key, read in readings.items():
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


def correct(conn, result_id, human_read, by):
    """A person says what the child actually wrote. `POST /capture/correct`, and the mechanism the
    approval screen exists for.

    Append-only, and deliberately so (rule 4): the machine's own reading stays in
    `item_result.raw_read` untouched for ever, and the correction is a NEW `read_correction` row.
    Two things depend on that. A teacher can always see what the engine made of their child's
    handwriting, and the flag rate and the silent-error rate stay measurable afterwards — overwrite
    the read and the engine can never again be scored against the page it read.

    Only the MARK is recomputed, by the same `mark` the import path uses, because marking is a
    lookup against numbers computed when the paper was entered. A teacher is asked what a child
    wrote, never whether it is right.
    """
    row = conn.execute(
        "select r.id, r.tenant_id, r.raw_read, r.capture_id, si.child_id, i.spec, i.responses"
        " from item_result r join item i on i.id = r.item_id"
        " join capture c on c.id = r.capture_id join sheet_instance si on si.id = c.sheet_instance_id"
        " where r.id = %s and r.state = 'candidate'",
        (result_id,),
    ).fetchone()
    if not row:
        raise ValueError(f"no answer waiting for a person with id {result_id}")
    read = (
        json.loads(row["raw_read"] or "{}") if isinstance(row["raw_read"], str) else (row["raw_read"] or {})
    )
    text = (human_read or "").strip()
    reading = {**read, "child_answer": text, "answer_state": "written" if text else "blank"}
    status, codes, working = mark(row["spec"], row["responses"][0], reading)
    conn.execute(
        "insert into read_correction (tenant_id, child_id, capture_id, item_result_id, model_read,"
        " human_read, misconception_codes, by) values (%s,%s,%s,%s,%s,%s,%s,%s)",
        (
            row["tenant_id"],
            row["child_id"],
            row["capture_id"],
            row["id"],
            read.get("child_answer", "") or "",
            text,
            codes,
            by,
        ),
    )
    conn.execute(
        "update item_result set status = %s, misconception_codes = %s, working_shown = %s,"
        " updated_at = now() where id = %s",
        (status, codes, working, row["id"]),
    )
    return {"status": status, "codes": codes, "was": read.get("child_answer", "") or "", "now": text}


def corrections(conn):
    """Every answer a person has said the true reading of, latest first per answer.

    This is the gold set growing by use rather than by a data-entry project: a teacher confirming
    one paper hands the eval a handful of hand-verified responses, on the exact page a child wrote.
    """
    return conn.execute(
        "select distinct on (rc.item_result_id) t.batch_id as paper, c.path, i.item_key,"
        " rc.human_read, rc.by, rc.created_at"
        " from read_correction rc"
        " join item_result r on r.id = rc.item_result_id"
        " join item i on i.id = r.item_id"
        " join capture c on c.id = rc.capture_id"
        " join sheet_instance si on si.id = c.sheet_instance_id"
        " join sheet_template t on t.id = si.sheet_template_id"
        " where c.superseded_by is null"
        " order by rc.item_result_id, rc.created_at desc"
    ).fetchall()


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
