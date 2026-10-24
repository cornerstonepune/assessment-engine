"""An English sample as the educator's form holds it, and back (goals/edt_edit_samples_and_kinds.yaml): every list one
line per item, so a person types what a child sees without writing a data format. The website sends the form's words;
the engine reads them into the stored shape here, checks them (english_check.py) and stores them.

- options: one per line; a match has a column of lines on each side (`left`, `right`)
- the right answer: words; for an order or words to mark, one per line; a match, a line per pair “left - right”; a
  sort, a line per item “item: group” (as a wrong answer is written); a table, a line per box “box: what goes in it”
- other answers taken as right, what a right answer does, words shown on purpose that are not words: one per line
"""

from typing import Any

LISTS = {"ENG.ORDER", "ENG.MARK_WORDS"}
PAIR, GROUP = " - ", ": "


def lines(text: str | None) -> list[str]:
    return [x.strip() for x in (text or "").splitlines() if x.strip()]


def _answer_out(kind: str, a: Any) -> str:
    if kind == "ENG.MATCH":
        return "\n".join(f"{x}{PAIR}{y}" for x, y in a)
    if kind == "ENG.SORT":
        return "\n".join(f"{i}{GROUP}{g}" for g, items in a.items() for i in items)
    if kind == "ENG.TABLE":
        return "\n".join(f"{k}{GROUP}{v}" for k, v in a.items())
    return "\n".join(a) if isinstance(a, list) else str(a or "")


def _answer_in(kind: str, text: str) -> Any:
    rows = lines(text)
    if kind == "ENG.MATCH":
        return [r.split(PAIR, 1) if PAIR in r else [r, ""] for r in rows]
    if kind in ("ENG.SORT", "ENG.TABLE"):
        # split at the last ": ", since a box may name its row and column ("Camel: where it lives")
        split = [r.rsplit(GROUP, 1) if GROUP in r else [r, ""] for r in rows]
        if kind == "ENG.TABLE":
            return {k.strip(): v.strip() for k, v in split}
        groups: dict[str, list[str]] = {}
        for item, group in split:
            groups.setdefault(group.strip(), []).append(item.strip())
        return groups
    if kind in LISTS or (kind == "ENG.COPY" and len(rows) > 1):
        return rows
    return "\n".join(rows)


def to_form(kind: str, s: dict[str, Any]) -> dict[str, Any]:
    """A stored sample as the form shows it."""
    opts = s.get("options")
    match = isinstance(opts, dict)
    return {
        "ask": s.get("ask") or "",
        "text": s.get("text") or "",
        "options": "" if match else "\n".join(opts or []),
        "left": "\n".join(opts.get("left", [])) if match else "",
        "right": "\n".join(opts.get("right", [])) if match else "",
        "answer": _answer_out(kind, s.get("answer")),
        "accept": "\n".join(s.get("accept") or []),
        "key_points": "\n".join(s.get("key_points") or []),
        "not_words": "\n".join(s.get("not_words") or []),
    }


def from_form(kind: str, f: dict[str, Any]) -> dict[str, Any]:
    """The form's words as a sample is stored. A box left empty is no list (None), as the seed has it."""
    if kind == "ENG.MATCH":
        options: Any = {"left": lines(f.get("left")), "right": lines(f.get("right"))}
    else:
        options = lines(f.get("options")) or None
    return {
        "question_type": kind,
        "ask": (f.get("ask") or "").strip(),
        "text": (f.get("text") or "").strip() or None,
        "options": options,
        "answer": _answer_in(kind, f.get("answer") or ""),
        "accept": lines(f.get("accept")),
        "key_points": lines(f.get("key_points")) or None,
        "not_words": lines(f.get("not_words")) or None,
    }
