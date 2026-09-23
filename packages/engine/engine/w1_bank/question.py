"""One question in the bank, on its own: how it prints, and a person's correction to it.

The question page shows a question exactly as a paper prints it — the same `render_item`, the same
stylesheet — so a person checks what a child will see, not a second drawing of it.

A correction rewords a question and can do nothing else. Code checks that the new sentence states
exactly the numbers the old one did, so the answer and every wrong answer the question catches —
all computed from those numbers — stay right whatever a person types. The correction is a new
question that points at the old one; the old one is retired with who and why, never rewritten
(Ring A: append or approve).
"""

import json
import re

from playwright.sync_api import sync_playwright

from engine.assess import render, verify
from engine.assess.items import _id
from engine.assess.pick import Sheet
from engine.w1_bank import inventory
from engine.w2_print import library

# Kinds whose printed line is drawn from their numbers, not from `item.stem` (`render.render_item`
# replaces the stem for these three): rewording one would change nothing on paper.
DRAWN_FROM_NUMBERS = {"bare_sum", "column_grid", "missing_number"}


def _row(conn, item_key):
    return conn.execute(
        "select i.*, r.band from item i join rung r on r.tenant_id = i.tenant_id and r.code = i.rung_code"
        " where i.item_key = %s and i.source = 'generated'",
        (item_key,),
    ).fetchone()


def printed(conn, item_key) -> bytes | None:
    """The question's own block of a printed page as a PNG, at the width of a page's text (178 mm).
    Where it sits on a page depends on the questions around it; how it looks does not."""
    row = _row(conn, item_key)
    if not row:
        return None
    it = inventory.item_from_row(row)
    block = render.render_item(Sheet("CS000000", row["band"], row["difficulty"], 1, "preview", [it]), it, 1)
    page = (
        f'<!doctype html><html><head><meta charset="utf-8"><style>{render.CSS}</style></head>'
        f'<body><div id="q" style="width:178mm;padding:3mm 2mm 1mm">{block}</div></body></html>'
    )
    # ponytail: a browser per view (~1 s); cache by item_key if the question page is ever busy.
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            tab = browser.new_page(viewport={"width": 794, "height": 1123}, device_scale_factor=2)
            tab.set_content(page)
            return tab.locator("#q").screenshot()
        finally:
            browser.close()


def _numbers(text):
    """Every number a sentence states, commas dropped (₹12,000 is 12000)."""
    return sorted(re.findall(r"\d+", text.replace(",", "")))


def _refusal(old, stem, reason):
    """Why this rewording cannot be taken, in the words shown to the person — or None."""
    if not reason:
        return "A correction needs a reason, so the next person knows what was wrong."
    if old["status"] != "active":
        return "Only a question that is ready to print can be corrected."
    if old["fmt"] in DRAWN_FROM_NUMBERS:
        return "This kind of question prints from its numbers alone, so it has no wording to correct. Remove it instead."
    if stem == old["stem"]:
        return "The wording is the same as before."
    if _numbers(stem) != _numbers(old["stem"]):
        return (
            "Keep every number exactly as it was, written in digits. To change a number, remove this "
            "question instead: the bank has others at this level."
        )
    banned = next((w for w in verify.FORBIDDEN_WORDS if re.search(rf"\b{w}", stem, re.I)), None)
    if banned:
        return f"The school says 'exchange' or 'regroup', never '{banned}'."
    return None


def correct(conn, item_key, stem, by, reason) -> dict:
    """Reword one question. Raises LookupError for an unknown question and ValueError, with the
    reason in words, for a rewording that is refused — in which case nothing has changed."""
    stem, reason = " ".join(stem.split()), " ".join(reason.split())
    if not by:
        raise ValueError("A correction must name the person making it.")
    old = _row(conn, item_key)
    if not old:
        raise LookupError(f"no question {item_key!r} in the bank")
    refused = _refusal(old, stem, reason)
    if refused:
        raise ValueError(refused)

    # The bank's own key scheme; the wording joins the numbers, as two wordings are two rows.
    new_key = _id(old["template"], f"{json.dumps(old['spec'], sort_keys=True)}|{stem}")
    new = conn.execute(
        "insert into item (tenant_id, item_key, template, rung_code, skill_codes, signal, fmt, stem, spec,"
        " responses, tags, case_codes, source, status, skill_set_code, difficulty, eval_type, skill_set_version,"
        " generator, corrected_from)"
        " select tenant_id, %s, template, rung_code, skill_codes, signal, fmt, %s, spec, responses, tags, case_codes,"
        " source, 'active', skill_set_code, difficulty, eval_type, skill_set_version, 'correction', id"
        " from item where id = %s"
        " on conflict (tenant_id, item_key) do nothing returning id",
        (new_key, stem, old["id"]),
    ).fetchone()
    if not new:
        raise ValueError("That wording is already in the bank.")
    # A child who saw the old wording has seen this question: the exposure window must still hold.
    conn.execute(
        "insert into item_exposure (tenant_id, child_id, item_id, week, created_at)"
        " select tenant_id, child_id, %s, week, created_at from item_exposure where item_id = %s"
        " on conflict do nothing",
        (new["id"], old["id"]),
    )
    inventory.flag(conn, item_key, by, f"Corrected as {new_key}: {reason}")
    library.build(conn, only=(old["skill_set_code"], old["difficulty"]))
    return {"item_key": new_key, "retired": item_key}


def remove(conn, item_key, by, note) -> dict:
    """Any staff member takes a question out of the bank, with one line of why. The worksheets it
    was on are retired and replaced in the same transaction, so no worksheet ever holds a question
    that has left the bank (ADR 0026). Raises LookupError for an unknown question."""
    if not by:
        raise ValueError("Removing a question must name the person removing it.")
    old = _row(conn, item_key)
    if not old:
        raise LookupError(f"no question {item_key!r} in the bank")
    status = inventory.flag(conn, item_key, by, " ".join(note.split()))
    changed = library.build(conn, only=(old["skill_set_code"], old["difficulty"]))
    return {"item_key": item_key, "status": status, "worksheets_retired": changed["retired"]}
