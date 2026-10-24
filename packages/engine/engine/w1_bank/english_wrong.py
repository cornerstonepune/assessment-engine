"""The likely wrong answers of an English sample (goals/edt_edit_samples_and_kinds.yaml), from research/english_wrong.py:
each names one of the skill's mistakes, differs from the right answer and from the others, and is an answer the question
could really get. What "could really get" means depends on the kind: a choice is a printed option; an order is every
item, once, in another order ("a, b, c"); a match is a pair the key does not make ("left - right"); a sort puts an item
in a group it does not belong to ("item: group"); a table box holds what the key does not ("box: words"); marked or
copied words are in the text; punctuating keeps the words.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from engine.w1_bank import english_words as ew

if TYPE_CHECKING:
    from engine.w1_bank.english_check import Context, Faults, Sample


def _is_order(w: str, items: list[str]) -> bool:
    """w is every item once, joined by ', ' (items may hold commas, so they are matched, not split)."""
    left, rest = list(items), w
    while left:
        hit = next(
            (i for i in sorted(left, key=len, reverse=True) if rest == i or rest.startswith(i + ", ")), None
        )
        if hit is None:
            return False
        left.remove(hit)
        rest = rest[len(hit) + 2 :] if len(rest) > len(hit) else ""
    return rest == ""


def _fits_choice(w: str, s: Sample, c: Context) -> str:
    return "" if w in (s.get("options") or []) else "is not one of the printed options"


def _fits_order(w: str, s: Sample, c: Context) -> str:
    if not _is_order(w, s.get("options") or []):
        return "is not every item once, in an order, with a comma between them"
    return "is the right order" if w == ", ".join(s.get("answer") or []) else ""


def _fits_match(w: str, s: Sample, c: Context) -> str:
    o = s.get("options") or {}
    pairs = [[a, b] for a in o.get("left", []) for b in o.get("right", []) if w == f"{a} - {b}"]
    if not pairs:
        return "is not a word on the left joined to one on the right, written “left - right”"
    return "is a pair the key makes" if pairs[0] in [list(x) for x in s.get("answer") or []] else ""


def _fits_sort(w: str, s: Sample, c: Context) -> str:
    ans = s.get("answer") or {}
    hits = [(i, g) for i in s.get("options") or [] for g in ans if ew.plain(w) == ew.plain(f"{i}: {g}")]
    if not hits:
        return "is not an item and a group, written “item: group”"
    return "puts the item where the key puts it" if hits[0][0] in ans[hits[0][1]] else ""


def _fits_table(w: str, s: Sample, c: Context) -> str:
    ans = s.get("answer") or {}
    hits = [k for k in ans if ew.plain(w).startswith(ew.plain(f"{k}: "))]
    if not hits:
        return "is not a box of the table and what a child writes in it, written “box: words”"
    return (
        "is what the key puts in the box" if ew.plain(w[len(hits[0]) + 2 :]) == ew.plain(ans[hits[0]]) else ""
    )


def _fits_mark(w: str, s: Sample, c: Context) -> str:
    parts = [x.strip() for x in w.split(",") if x.strip()]
    if not parts or not all(ew.found(x, s.get("text") or c.passage) for x in parts):
        return "marks words that are not in the text"
    same = sorted(map(ew.plain, parts)) == sorted(map(ew.plain, s.get("answer") or []))
    return "marks exactly the right words" if same else ""


def _fits_copy(w: str, s: Sample, c: Context) -> str:
    return "" if ew.found(w, c.passage) else "is not copied from the passage"


def _fits_punctuate(w: str, s: Sample, c: Context) -> str:
    return "" if ew.same_words(s.get("text"), w) else "changes the words instead of the punctuation"


FITS: dict[str, Callable[[str, Sample, Context], str]] = {
    "ENG.CHOOSE": _fits_choice,
    "ENG.ORDER": _fits_order,
    "ENG.MATCH": _fits_match,
    "ENG.SORT": _fits_sort,
    "ENG.TABLE": _fits_table,
    "ENG.MARK_WORDS": _fits_mark,
    "ENG.COPY": _fits_copy,
    "ENG.PUNCTUATE": _fits_punctuate,
}


def _fits(q: str, w: str, s: Sample, c: Context) -> str:
    if q == "ENG.GAP" and s.get("options"):
        return _fits_choice(w, s, c)
    return FITS[q](w, s, c) if q in FITS else ""


def check(s: Sample, c: Context) -> Faults:
    wrong = [w for w in s.get("wrong") or [] if (w.get("answer") or "").strip()]
    if not wrong:
        return {"wrong": ["Give at least one likely wrong answer, and the mistake it shows."]}
    f: Faults = {}
    right = {ew.plain(x) for x in [str(s.get("answer")), *(s.get("accept") or [])] if isinstance(x, str)}
    seen: set[str] = set()
    for i, w in enumerate(s.get("wrong") or []):
        text, why = (w.get("answer") or "").strip(), []
        if not text:
            if w.get("mistake_code"):
                f[f"wrong.{i}"] = ["Write the wrong answer this mistake gives, or leave its mistake empty."]
            continue
        if w.get("mistake_code") not in c.mistakes:
            why.append("Choose the mistake it shows, from the mistakes of this skill.")
        if ew.plain(text) in right:
            why.append(f"{ew.quoted(text)} is a right answer, not a wrong one.")
        elif ew.plain(text) in seen:
            why.append(f"{ew.quoted(text)} is listed twice.")
        elif fit := _fits(s["question_type"], text, s, c):
            why.append(f"{ew.quoted(text)} {fit}.")
        seen.add(ew.plain(text))
        if why:
            f[f"wrong.{i}"] = why
    return f
