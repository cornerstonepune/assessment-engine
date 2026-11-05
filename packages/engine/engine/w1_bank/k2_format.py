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
from collections.abc import Callable, Iterable

from engine.w1_bank import k2_batch as batch

Judge = Callable[[object, dict[str, list[str]]], tuple[dict[str, dict], dict[str, str]]]
BULLET = "•"


def _head_nouns(materials: str) -> set[str]:
    """The last word of each thing a materials text lists ("Number cards 1-10" → card), the noun a step would name."""
    out: set[str] = set()
    for piece in re.split(r"[,;\n]+|\band\b", re.sub(r"\([^)]*\)", " ", materials or ""), flags=re.I):
        toks = batch._tokens(re.sub(r"[^A-Za-z ]", " ", piece))
        if toks and len(toks[-1]) >= 3:
            out.add(toks[-1])
    return out


def vocabulary(texts: Iterable[str]) -> frozenset[str]:
    """The nouns that name a material anywhere in the band's materials texts."""
    return frozenset().union(*(_head_nouns(t) for t in texts))


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


def _unlisted(steps: list[str], uses: object, materials: str, vocab: frozenset[str], fmt: dict) -> str:
    """A thing a step or the page's own `uses` names that the school's materials text does not."""
    pieces = [batch._tokens(p) for p in re.split(r"[,;\n]+", materials)]
    for name in uses if isinstance(uses, list) else []:
        phrase = batch._tokens(re.sub(r"[^A-Za-z ]", " ", str(name)))
        if phrase and batch._segment_with(pieces, phrase) is None:
            return f"uses '{name}': not in the school's materials"
    mine = {t for toks in pieces for t in toks}
    free = {batch._stem(w.casefold()) for w in fmt["always_there"]}
    for i, step in enumerate(steps, 1):
        for word in re.findall(r"[a-z]+", step.casefold()):
            stem = batch._stem(word)
            if stem in vocab and stem not in mine and stem not in free:
                return f"steps line {i} uses '{word}', which the school's materials do not name"
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
