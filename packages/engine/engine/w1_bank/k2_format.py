"""The shape of a drafted K2 page, judged by code (goals/m1-12a-page-format.yaml, task M1-12a).

A page is read on a screen as bullets with the keywords highlighted, and a ten-second video is made from it later, so
the steps are a list (a few short lines), the thinking is one line and a list of slips (a keyword and how to spot it),
and no step may use a thing the school's materials do not name. The limits are a config row (`k2.format`). The model
says what the steps use (`uses`) and code checks that against the school's text; code also reads every step against the
words that name materials anywhere in the band, which catches a thing used but never declared. Limit, stated: it can
only see a material that some page of the band names, and it reads a noun, not whether the step makes sense; the
checker (a stronger model, shown only the school's words) is the judge of that. Pure: no database, no model.
"""

import re
from collections import Counter
from collections.abc import Callable, Iterable
from typing import LiteralString

from engine.w1_bank import k2_batch as batch

Judge = Callable[[object, dict[str, list[str]]], tuple[dict[str, dict], dict[str, str]]]
BULLET = "•"
LISTS: dict[str, LiteralString] = {"steps": "steps_list", "thinking": "thinking_doc"}  # a part's list column


def _words(text: str) -> list[str]:
    """The words of a text, each as one word for its thing (no digits)."""
    return [t for t in batch._tokens(text) if t.isalpha()]


def _head_nouns(materials: str, function_words: frozenset[str], not_props: frozenset[str]) -> set[str]:
    """The noun each thing a materials text lists is named by: the last word of a short name ("Number cards 1-10" →
    card). The words of the language that trail a name ("as needed", "for the") are not part of it; a piece with such a
    word inside is a clause ("cards to point at", "place the blocks"), not the name of a thing, and names none."""
    out: set[str] = set()
    listed = (re.sub(r"\([^)]*\)", " ", p) for p in batch.pieces_of(materials))
    for piece in (q for p in listed for q in re.split(r"\band\b", p, flags=re.I)):
        toks = _words(piece)
        while toks and toks[-1] in function_words | not_props:
            toks.pop()
        if toks and len(toks[-1]) >= 3 and not any(t in function_words for t in toks):
            out.add(toks[-1])
    return out


def vocabulary(
    texts: Iterable[str],
    function_words: Iterable[str] = (),
    min_pages: int = 1,
    not_props: Iterable[str] = (),
) -> frozenset[str]:
    """The nouns that name a material on at least `min_pages` pages of the band (`texts` holds one page's list each): a
    thing that is listed again and again is a prop; a word that ends a clause of one list is not."""
    skip, generic = (frozenset(batch._tokens(" ".join(words))) for words in (function_words, not_props))
    pages = Counter(w for t in texts for w in _head_nouns(t, skip, generic))
    return frozenset(w for w, n in pages.items() if n >= min_pages)


def _count(text: str) -> int:
    return len(text.split())


def _lines(value: object, fmt: dict) -> tuple[list[str], str]:
    if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
        return [], "steps must be a list of lines"
    lines = [re.sub(r"^\s*(?:\d+[.)]|[-*•])\s*", "", x).strip() for x in value]
    lines = [x for x in lines if x]
    if not lines:
        return [], "steps is empty"
    if len(lines) > fmt["steps_max"]:
        return [], f"steps has {len(lines)} lines, at most {fmt['steps_max']}"
    for i, line in enumerate(lines, 1):
        if _count(line) > fmt["step_words"]:
            return [], f"steps line {i} has {_count(line)} words, at most {fmt['step_words']}"
    return lines, ""


def _slips(value: object, fmt: dict) -> tuple[list[dict[str, str]], str]:
    if not isinstance(value, list) or not fmt["slips_min"] <= len(value) <= fmt["slips_max"]:
        n = len(value) if isinstance(value, list) else 0
        return [], f"slips: {fmt['slips_min']} to {fmt['slips_max']} wanted, got {n}"
    out: list[dict[str, str]] = []
    for i, s in enumerate(value, 1):
        if (
            not isinstance(s, dict)
            or not isinstance(s.get("keyword"), str)
            or not isinstance(s.get("spot"), str)
        ):
            return [], f"slips item {i} is not a keyword and a spot"
        keyword, spot = s["keyword"].strip(), s["spot"].strip()
        if not fmt["keyword_words_min"] <= _count(keyword) <= fmt["keyword_words_max"]:
            return [], (
                f"slips item {i} keyword must be {fmt['keyword_words_min']} to {fmt['keyword_words_max']} words"
            )
        if not spot or _count(spot) > fmt["spot_words"]:
            return [], f"slips item {i} spot must be one short sentence of at most {fmt['spot_words']} words"
        out.append({"keyword": keyword, "spot": spot})
    return out, ""


def _thinking(it: dict, fmt: dict) -> tuple[dict, str]:
    idea = it.get("idea")
    if not isinstance(idea, str) or not idea.strip():
        return {}, "idea is empty"
    if _count(idea) > fmt["idea_words"]:
        return {}, f"idea has {_count(idea)} words, at most {fmt['idea_words']}"
    slips, why = _slips(it.get("slips"), fmt)
    return ({"idea": idea.strip(), "slips": slips}, "") if not why else ({}, why)


def _covered(phrase: list[str], pieces: list[list[str]]) -> bool:
    """Every word of a use stands in the list, each run of words inside one piece of it, in that order."""
    i = 0
    while i < len(phrase):
        k = next(
            (k for k in range(len(phrase) - i, 0, -1) if batch._segment_with(pieces, phrase[i : i + k])), 0
        )
        if not k:
            return False
        i += k
    return True


def _use_unlisted(uses: object, pieces: list[list[str]], function_words: frozenset[str]) -> str:
    for name in uses if isinstance(uses, list) else []:
        phrase = [t for t in _words(str(name)) if t not in function_words]
        if phrase and not _covered(phrase, pieces):
            return f"uses '{name}': not in the school's materials"
    return ""


def unlisted_step_words(
    steps: list[str], materials: str, vocab: frozenset[str], fmt: dict
) -> list[tuple[int, str]]:
    """Every (line, word) of the steps that names a prop of the band which the page's own materials text does not. A page
    the school gave no list names none (its steps are read by the checker)."""
    mine = {t for toks in (_words(p) for p in batch.pieces_of(materials)) for t in toks}
    free = {batch._stem(w.casefold()) for w in fmt["always_there"]}
    out: list[tuple[int, str]] = []
    for i, step in enumerate(steps if mine else [], 1):
        # the first word is the verb the prompt asks for
        for word in re.findall(r"[a-z]+", step.casefold())[1:]:
            stem = batch._stem(word)
            if stem in vocab and stem not in mine and stem not in free:
                out.append((i, word))
    return out


def _unlisted(steps: list[str], uses: object, materials: str, vocab: frozenset[str], fmt: dict) -> str:
    """A thing a step or the page's own `uses` names that the school's materials text does not. A page the school gave
    no list is judged by its `uses` alone (it must be empty); its steps are read by the checker."""
    # words only, on both sides: "Beads (10 per child)" is listed as bead, per, child whichever way the digits were kept
    pieces = [_words(p) for p in batch.pieces_of(materials)]
    skip = frozenset(batch._tokens(" ".join(fmt.get("function_words", []))))
    if why := _use_unlisted(uses, pieces, skip):
        return why
    if found := unlisted_step_words(steps, materials, vocab, fmt):
        line, word = found[0]
        return f"steps line {line} uses '{word}', which the school's materials do not name"
    return ""


def render(part: str, value: object) -> str:
    """A part as the text the page's column holds (the site and the upload already read text)."""
    if part == "steps" and isinstance(value, list):
        return "\n".join(f"{BULLET} {x}" for x in value)
    if part == "thinking" and isinstance(value, dict):
        slips = [f"{BULLET} {s['keyword']}: {s['spot']}" for s in value["slips"]]
        return "\n".join([value["idea"], *slips])
    return str(value)


def shown_draft(parts: dict) -> str:
    """The draft as the checker reads it: bullets and slips, one per line."""
    out: list[str] = []
    for part, value in parts.items():
        if part == "steps":
            out += ["steps:", *[f"  {BULLET} {x}" for x in value]]
        elif part == "thinking":
            out += [
                f"idea: {value['idea']}",
                *[f"slip: {s['keyword']} — how to spot it: {s['spot']}" for s in value["slips"]],
            ]
        else:
            out.append(f"{part}: {value}")
    return "\n".join(out)


def judger(rows: dict, vocab: frozenset[str], fmt: dict, rules: dict | None) -> Judge:
    """→ `judge(got, want)`: the pages a reply gets right (their lists as lists) and why each other asked-for page is
    not. `rows[key]["materials"]` is the school's own text for that page."""

    def judge(got: object, want: dict[str, list[str]]):
        seen, twice = batch._by_key(got, want)
        flat: list[dict] = []
        structured: dict[str, dict] = {}
        faults: dict[str, str] = {}
        for key, parts in want.items():
            it = seen.get(key)
            if it is None or key in twice:
                continue  # judge_pages words these two
            made: dict[str, object] = {}
            why = ""
            if "steps" in parts:
                made["steps"], why = _lines(it.get("steps"), fmt)
                why = why or _unlisted(
                    made["steps"], it.get("uses"), rows[key]["materials"] or "", vocab, fmt
                )  # type: ignore[arg-type]
            if "thinking" in parts and not why:
                made["thinking"], why = _thinking(it, fmt)
            if why:
                faults[key] = why
                continue
            structured[key] = made
            flat.append(it | {p: render(p, v) for p, v in made.items()})
        asked = {k: v for k, v in want.items() if k not in faults}
        good, bad = batch.judge_pages(flat or [{}], asked, rules)
        for key, parts in structured.items():
            if key in good:
                good[key] |= parts
        return good, bad | faults

    return judge


def lines_of(text: str) -> list[str]:
    """The lines of a text as bullets read them: one to a line, the bullet or number in front taken off."""
    out = (re.sub(r"^\s*(?:\d+[.)]|[-*\u2022])\s*", "", ln).strip() for ln in (text or "").splitlines())
    return [x for x in out if x]


def edited(part: str, value: object) -> object:
    """A person's own words for a part, as the site sends them: text for any part; for the steps a list of lines; for the
    thinking an idea and a list of slips. Refused if it is not that, so nothing malformed reaches a page. The AI-format
    limits (how many, how long) are for drafts: a person may write what they like."""
    if isinstance(value, str):
        if not value.strip():
            raise ValueError("a part changed to nothing is a rejected draft: use reject")
        return value.strip()
    if part == "steps" and isinstance(value, list):
        lines = [x.strip() for x in value if isinstance(x, str) and x.strip()]
        if not lines or len(lines) != len(value):
            raise ValueError("steps must be a list of lines, none empty")
        return lines
    if part == "thinking" and isinstance(value, dict):
        idea, slips = value.get("idea"), value.get("slips")
        if not isinstance(idea, str) or not idea.strip() or not isinstance(slips, list):
            raise ValueError("thinking must be an idea and a list of slips")
        kept = []
        for s in slips:
            if not isinstance(s, dict) or not all(
                isinstance(s.get(k), str) and s[k].strip() for k in ("keyword", "spot")
            ):
                raise ValueError("each slip must be a keyword and how to spot it")
            kept.append({"keyword": s["keyword"].strip(), "spot": s["spot"].strip()})
        return {"idea": idea.strip(), "slips": kept}
    raise ValueError(f"{part} cannot be changed to that")
