"""One child's scanned pages → readings, with the child's notebook open (ADR 0032).

Shared by the import (`legacy.import_scan`), the re-read (`engine read again`) and the replay
(`engine read replay`), so the reader in service and the reader under test are one function. The
order on each page: the first reader (Textract behind the engine's geometry, ADR 0019) with this
child's own confidence floor; the notebook's flags (a routed kind, a confused digit); then the second
reader's guess for whatever is left doubted.
"""

from engine.adapters import ocr
from engine.w3_read import profiles, second_reader, stencil


def read_pages(conn, scan, cli, child_id, notes=None, second=True):
    """`scan`: path, paper_code, paper (the key), by_key, page_numbers, images, masks. → one dict per
    page: page_no, the masked jpeg, the readings (None where the page prints no answers) and a note
    for a person. `notes` overrides the child's stored notebook — the replay passes the notebook built
    without this paper, or none."""
    path, paper_code, paper, by_key = scan["path"], scan["paper_code"], scan["paper"], scan["by_key"]
    page_numbers, images, masks = scan["page_numbers"], scan["images"], scan.get("masks")
    from engine.w3_read import legacy

    cfg = ocr.settings(conn)
    if notes is None:
        notes = profiles.current(conn, child_id) if child_id else {}
    if notes.get("floor"):
        cfg = {**cfg, "min_confidence": float(notes["floor"])}
    page_specs = {p["n"]: p for p in paper.get("pages", [{"n": 1}])}
    out = []
    for page_no, jpeg in zip(page_numbers, images):
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
        readings = stencil.read_page(
            jpeg,
            questions,
            cfg,
            cli,
            form=paper.get("printed_as", paper_code),
            page_no=page_no,
            symbolic=legacy.symbolic_slots(by_key),
            use_boxes=paper.get("fields") == "boxes",
            reread=legacy.second_look(path, page_no, fraction, cfg, cli),
        )
        readings = profiles.apply(readings, notes, lambda k: (by_key.get(k) or {}).get("fmt", ""))
        note = ""
        if second:
            file_page = page_no if len(page_numbers) > 1 or page_no == 1 else 1
            readings, note = second_reader.propose(conn, readings, path, file_page, notes, cfg)
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
    return out
