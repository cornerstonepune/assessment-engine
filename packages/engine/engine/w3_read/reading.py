"""One child's scanned pages → readings, with the child's notebook open (ADR 0032).

Shared by the import (`legacy.import_scan`), the re-read (`engine read again`) and the replay
(`engine read replay`), so the reader in service and the reader under test are one function. The
order on each page: the first reader (Textract behind the engine's geometry, ADR 0019) with this
child's own confidence floor; the notebook's flags (a routed kind, a confused digit); then the second
reader's guess for whatever is left doubted.
"""

from engine.adapters import digits, ocr
from engine.w3_read import (
    boxes,
    crops,
    lists,
    marking,
    profiles,
    render_pdf,
    same_page,
    second_reader,
    stencil,
)


def _by_region(scan, page_no, questions, jpeg, fraction, cfg, cli):
    """A page of a paper entered by hand, which records no boxes, read by its printed words (`stencil`): each answer
    found in the region below its question, which ends at the next question it is given."""
    path, paper, by_key = scan["path"], scan["paper"], scan["by_key"]
    from engine.w3_read import legacy

    return stencil.read_page(
        jpeg,
        questions,
        cfg,
        cli,
        form=paper.get("printed_as", scan["paper_code"]),
        page_no=page_no,
        symbolic=legacy.symbolic_slots(by_key),
        use_boxes=paper.get("fields") in ("boxes", "cells"),
        reread=legacy.second_look(path, page_no, fraction, cfg, cli),
    )


def _to_a_person(questions, by_key):
    """A page of a paper this system printed whose boxes were not found, whole to a person (goals/r2): read by its words
    instead, a page of pictures hands one field to several questions (22 Oct, one box to Q1, Q7 and Q8). Nothing on it
    is read or guessed; a number not found is the reader's failure, a tick or a reason a person's as ever."""
    out = {}
    for k in questions:
        number = _digits(marking.response_of(by_key[k]))
        state, why = ("not_found", boxes.UNALIGNED) if number else ("for_a_person", boxes.FOR_A_PERSON)
        out[k] = {"child_answer": "", "answer_state": state, "why": why, "guess": "", "confidence": 0.0}
    return out


def _not_found(page_no, by_key):
    """A page of the paper the copy's file has no photograph of — the photograph in its place was a page already
    (`placing.place`, goals/img_page_one_and_two_same_photo.yaml) — whole to a person, who is told in words. Every answer
    on it waits, a tick and a number alike: there is nothing to read, and no page is shown for it."""
    questions = {
        k: it["spec"]["question"] for k, it in by_key.items() if it["spec"].get("page", 1) == page_no
    }
    why = same_page.words(page_no)
    readings = {
        k: {"child_answer": "", "answer_state": "not_found", "why": why, "guess": "", "confidence": 0.0,
            "page": page_no, "page_found": False}
        for k in questions
    }  # fmt: skip
    return {"page_no": page_no, "jpeg": b"", "readings": readings or None, "note": f"p{page_no}: {why}"}


def _digits(response):
    return response.get("kind", "digits") == "digits"


def read_pages(conn, scan, cli, child_id, notes=None, second=True):
    """`scan`: path, paper_code, paper (the key), by_key, page_numbers, images, masks. → one dict per
    page: page_no, the masked jpeg, the readings (None where the page prints no answers) and a note
    for a person. `notes` overrides the child's stored notebook — the replay passes the notebook built
    without this paper, or none."""
    path, paper, by_key = scan["path"], scan["paper"], scan["by_key"]
    page_numbers, images, masks = scan["page_numbers"], scan["images"], scan.get("masks")
    from engine.w3_read import legacy

    cfg = ocr.settings(conn)
    if notes is None:
        notes = profiles.current(conn, child_id) if child_id else {}
    if notes.get("floor"):
        cfg = {**cfg, "min_confidence": float(notes["floor"])}
    page_specs = {p["n"]: p for p in paper.get("pages", [{"n": 1}])}
    file_pages = scan.get("file_pages") or list(range(1, len(images) + 1))
    out = []
    for page_no, jpeg, file_page in zip(page_numbers, images, file_pages):
        spec = page_specs.get(page_no) or {}
        fraction = (masks or {}).get(page_no, spec.get("mask", 0))
        jpeg = legacy.mask_name_band(jpeg, fraction)
        questions = {
            k: it["spec"]["question"] for k, it in by_key.items() if it["spec"].get("page", 1) == page_no
        }
        if not questions:
            out.append(
                {
                    "page_no": page_no,
                    "jpeg": jpeg,
                    "readings": None,
                    "note": f"p{page_no}: no answers printed on this page",
                }
            )
            continue
        # Textract, not a model: what reads a child's handwriting must not know arithmetic, because a
        # model that does fills faint pencil with the answer it can compute (ADR 0019). Measured on 45
        # hand-read responses: 80% exactly right with ZERO wrong readings the engine stood behind,
        # against 55-63% with about seven of them.
        # The paper says where its answers live (rule 1): only a paper that prints a box per answer
        # hands the reader its boxes. On an underline paper a stray rectangle is not a field.
        jpeg = ocr.mask_red_pen(jpeg, cfg)
        readings, how = None, ""
        if paper.get("geometry") and paper.get("printed"):
            # A paper this system printed: every box's place is recorded, so the boxes are cut out and read
            # where they are, and nothing outside them — the working — can be taken as the answer.
            on_page = {
                k: marking.response_of(it) for k, it in by_key.items() if it["spec"].get("page", 1) == page_no
            }
            wanted = {k: (by_key[k]["item_key"], r.get("rid", "ans")) for k, r in on_page.items()}
            # a tick or a sentence is not a number: the digit reader is never handed it, a person reads it
            people = {k for k, r in on_page.items() if r.get("kind", "digits") not in lists.READ}
            img, frame = render_pdf.photo(path, file_page)
            # the digit reader's own floor (ADR 0035), raised to this child's measured on that reader's readings
            # (`box_floor`): the child's floor from Textract's readings is on another scale. It only ever rises.
            floor = digits.settings(conn)
            floor["min_confidence"] = max(floor["min_confidence"], float(notes.get("box_floor") or 0))
            readings = boxes.read_page(
                img, page_no, paper["printed"], paper["geometry"], wanted, {**cfg, **floor}, frame=frame,
                keep=crops.keeper(path, page_no), for_a_person=people,
            )  # fmt: skip
            how = (
                "read in its boxes"
                if readings is not None
                else "did not line up with the paper it printed from"
            )
        if readings is None:
            readings = (_to_a_person(questions, by_key) if paper.get("geometry")
                        else _by_region(scan, page_no, questions, jpeg, fraction, cfg, cli))  # fmt: skip
        readings = profiles.apply(readings, notes, lambda k: (by_key.get(k) or {}).get("fmt", ""))
        note = how
        if (
            second
        ):  # the page of the file this image is, never the paper's: a copy may start at its third page
            # ADR 0091: a second opinion on the box reader's guesses, once its row turns it on
            opinion = second_reader.switched_on(conn)
            readings, proposed = second_reader.propose(
                conn, readings, path, file_page, notes, cfg, None, opinion
            )
            note = "; ".join(n for n in (how, proposed) if n)
        flagged = sum(1 for r in readings.values() if r["answer_state"] != "written")
        out.append(
            {
                "page_no": page_no,
                "jpeg": jpeg,
                "readings": readings,
                "note": f"p{page_no}: {len(readings)} answers read, {flagged} for a person"
                + (f"; {note}" if note else ""),
            }
        )
    # the pages of the paper the copy's file has no photograph of come after the photographs (`copies._read_copy`)
    return out + [_not_found(p, by_key) for p in page_numbers[len(images) :]]
