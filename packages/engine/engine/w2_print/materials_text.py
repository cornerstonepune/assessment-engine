"""The text the educator sends to the materials team and the one-tap link that opens WhatsApp with it (task M1-10;
D-071). A plain checklist, one line per item. The words are built here from rows, never by a model, and a quantity the
sheet does not give is said to be missing, never filled in."""

import datetime as dt
import re
from dataclasses import dataclass
from urllib.parse import quote


@dataclass(frozen=True)
class Line:
    item: str
    quantity: float | None
    unit: str
    needed_on: dt.date


def norm(s: object) -> str:
    """A word as the school's rows keep it: lower case, one space between words. The key an approved alias or unit is stored
    under and the key a note is looked up by must be this, character for character."""
    return " ".join(str(s).lower().split())


def day(d: dt.date) -> str:
    return f"{d:%a} {d.day} {d:%b}"


def short(d: dt.date) -> str:
    return f"{d.day} {d:%b}"


def number(q: float) -> str:
    return str(int(q)) if float(q).is_integer() else f"{q:g}"


def checklist(class_name: str, first: dt.date, last: dt.date, lines: list[Line]) -> str:
    out = [f"{class_name} materials, {short(first)} to {short(last)}"]
    for ln in lines:
        what = (
            f"{number(ln.quantity)} {ln.unit}"
            if ln.quantity is not None
            else f"quantity to confirm ({ln.unit})"
        )
        out.append(f"[ ] {ln.item}: {what}, needed {day(ln.needed_on)}")
    return "\n".join(out)


def whatsapp_link(text: str, to: str) -> str:
    """`https://wa.me/<number>?text=…`; with no number set (or one that is not digits) the chat opens with nobody chosen."""
    digits = re.sub(r"[\s+()-]", "", to or "")
    who = digits if digits.isdigit() else ""
    return f"https://wa.me/{who}?text={quote(text, safe='')}"
