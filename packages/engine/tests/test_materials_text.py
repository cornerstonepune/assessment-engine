"""What is sent to the materials team (task M1-10; D-071: "a proper checklist", one tap opens WhatsApp with the list
written out). Pure text: one line per item, and a link that opens WhatsApp with nobody chosen until the school names a
number. A quantity the sheet does not give is never filled in."""

import datetime as dt
from urllib.parse import parse_qs, urlsplit

from engine.w2_print import materials_text as t

LINES = [
    t.Line(item="Clay", quantity=2, unit="packet", needed_on=dt.date(2026, 11, 23)),
    t.Line(item="Smelling bottles", quantity=None, unit="piece", needed_on=dt.date(2026, 11, 25)),
]


def test_one_checklist_line_per_item_with_item_quantity_unit_and_the_day_needed():
    text = t.checklist("K2", dt.date(2026, 11, 23), dt.date(2026, 12, 4), LINES)
    body = text.splitlines()[1:]
    assert body == [
        "[ ] Clay: 2 packet, needed Mon 23 Nov",
        "[ ] Smelling bottles: quantity to confirm (piece), needed Wed 25 Nov",
    ]
    assert text.splitlines()[0] == "K2 materials, 23 Nov to 4 Dec"


def test_a_missing_quantity_is_never_made_up():
    assert (
        "0" not in t.checklist("K2", dt.date(2026, 11, 23), dt.date(2026, 11, 23), LINES[1:]).splitlines()[1]
    )


def test_a_whole_quantity_has_no_decimal_point():
    line = t.Line(item="Paper", quantity=2.0, unit="sheet", needed_on=dt.date(2026, 11, 23))
    assert "2 sheet" in t.checklist("K2", line.needed_on, line.needed_on, [line])
    half = t.Line(item="Rope", quantity=1.5, unit="metre", needed_on=dt.date(2026, 11, 23))
    assert "1.5 metre" in t.checklist("K2", half.needed_on, half.needed_on, [half])


def test_the_link_opens_whatsapp_with_the_text_and_nobody_chosen_when_no_number_is_set():
    link = t.whatsapp_link("a b\n[ ] Clay", "")
    parts = urlsplit(link)
    assert (parts.scheme, parts.netloc, parts.path) == ("https", "wa.me", "/")
    assert parse_qs(parts.query)["text"] == ["a b\n[ ] Clay"]


def test_the_link_chooses_the_number_the_school_names_digits_only():
    assert urlsplit(t.whatsapp_link("x", "+91 98765 43210")).path == "/919876543210"


def test_a_setting_that_is_not_a_number_chooses_nobody():
    assert urlsplit(t.whatsapp_link("x", "the materials group")).path == "/"
