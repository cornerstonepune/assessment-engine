"""Every English sample an educator saves is checked by code before it is stored (goals/edt_edit_samples_and_kinds.yaml;
CLAUDE.md: "code where correctness is needed"). Nimish, 2026-10-24: "It should simply have the capability to edit the
skill … or change the nature of the question." Ported from research/english_check.py, english_samples.py and
english_wrong.py, which checked the seed:

- the sample has the shape its kind needs, and a code-checked kind one right answer among its options or gaps;
- each likely wrong answer differs from the right one and from the others, is an answer the question could really get
  (a printed option, a real reorder, a pair or group the key does not make, words in the text), and names one of the
  skill's mistakes;
- every word is British English and the school's words hold (never "carry" or "borrow");
- an open kind, which a person reads, names the rubric it is read against and what a right answer does;
- the level's own rule holds (how many options, words, letters).

`faults` answers {field: [what is wrong, in words]}; empty when it may be stored. Not ported: working the right answer
out again by its rule (`worked_out`), which the seed carries and an educator's edit does not.
"""

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from engine.core import school_words
from engine.w1_bank import english_words as ew
from engine.w1_bank import english_wrong

GAP = "___"
Sample = dict[str, Any]
Faults = dict[str, list[str]]


@dataclass(frozen=True)
class Context:
    """What a sample is checked against: whether its kind is read by a person, the skill's mistakes {code: name}, its
    level's rule, the rubrics the skill may use, and the text of the passage it is about."""

    open: bool
    mistakes: dict[str, str]
    rule: dict[str, Any] = field(default_factory=dict)
    rubrics: set[str] = field(default_factory=set)
    passage: str = ""


def flat(v: Any) -> list[str]:
    if v is None:
        return []
    if isinstance(v, str):
        return [v]
    if isinstance(v, dict):
        return [x for k, val in v.items() for x in [k, *flat(val)]]
    return [x for i in v for x in flat(i)]


# — the shape each kind needs ——————————————————————————————————————————————————————————————————————————————


def _choose(s: Sample, c: Context) -> Faults:
    opts, ans = s.get("options"), s.get("answer")
    if not isinstance(opts, list) or len(opts) < 2 or len({ew.plain(o) for o in opts}) != len(opts):
        return {"options": ["A choice needs two or more different options."]}
    return (
        {} if ans in opts else {"answer": [f"The right answer {ew.quoted(ans)} is not one of the options."]}
    )


def _gap(s: Sample, c: Context) -> Faults:
    f: Faults = {}
    gaps = (s.get("text") or "").count(GAP)
    if gaps != 1:
        f["text"] = [f"A gap question has one gap, written {GAP}, in its sentence; this has {gaps}."]
    opts = s.get("options")
    if opts and s.get("answer") not in opts:
        f["answer"] = [f"The right answer {ew.quoted(s.get('answer'))} is not in the box of words."]
    return f


def _match(s: Sample, c: Context) -> Faults:
    opts, ans = s.get("options") or {}, s.get("answer") or []
    left, right = opts.get("left", []), opts.get("right", [])
    if not left or not right:
        return {"options": ["A match needs a column of words on each side."]}
    ok = all(isinstance(p, list) and len(p) == 2 for p in ans)
    if not ok or sorted(a for a, _ in ans) != sorted(left) or not all(b in right for _, b in ans):
        return {"answer": ["Each word on the left is joined to one word on the right, once."]}
    return {}


def _order(s: Sample, c: Context) -> Faults:
    ans = s.get("answer")
    if not isinstance(ans, list) or sorted(ans) != sorted(s.get("options") or []) or len(ans) < 2:
        return {"answer": ["The right order uses every item, once."]}
    return {}


def _sort(s: Sample, c: Context) -> Faults:
    ans = s.get("answer")
    got = [i for v in ans.values() for i in v] if isinstance(ans, dict) and ans else None
    if got is None or sorted(got) != sorted(s.get("options") or []):
        return {"answer": ["Each item goes in exactly one group."]}
    return {}


def _write_word(s: Sample, c: Context) -> Faults:
    ans = s.get("answer")
    if not isinstance(ans, str) or not ans.strip() or len(ans.split()) > 2:
        return {"answer": ["The word to write is one word (or two, for a short form)."]}
    return {}


def _mark(s: Sample, c: Context) -> Faults:
    ans = s.get("answer")
    if not isinstance(ans, list) or not ans or not all(ew.found(w, s.get("text") or c.passage) for w in ans):
        return {"answer": ["The words to mark are words in the text."]}
    return {}


def _copy(s: Sample, c: Context) -> Faults:
    if not c.passage:
        return {"passage": ["Copying needs a passage to copy from."]}
    ans = s.get("answer")
    parts = ans if isinstance(ans, list) else [ans] if isinstance(ans, str) else []
    if not parts or not all(ew.found(w, c.passage) for w in parts):
        return {"answer": ["The words to copy are words of the passage."]}
    return {}


def _punctuate(s: Sample, c: Context) -> Faults:
    ans = s["answer"] if isinstance(s.get("answer"), str) else ""
    if not ew.same_words(s.get("text"), ans) or not re.search(r"[.?!][\"”']?$", ans.strip()):
        return {
            "answer": ["Punctuating keeps every word of the sentence and ends it with a full stop, ? or !."]
        }
    return {}


def _correct(s: Sample, c: Context) -> Faults:
    if ew.plain(s.get("text")) == ew.plain(s.get("answer") if isinstance(s.get("answer"), str) else ""):
        return {"answer": ["The corrected sentence changes something."]}
    return {}


def _table(s: Sample, c: Context) -> Faults:
    ans = s.get("answer")
    if not isinstance(ans, dict) or not ans or not all(str(v).strip() for v in ans.values()):
        return {"answer": ["Each box of the table has what goes in it."]}
    return {}


def _said(s: Sample, c: Context) -> Faults:
    ans = s.get("answer")
    return {} if isinstance(ans, str) and ans.strip() else {"answer": ["Write the right answer."]}


SHAPES: dict[str, Callable[[Sample, Context], Faults]] = {
    "ENG.CHOOSE": _choose,
    "ENG.GAP": _gap,
    "ENG.MATCH": _match,
    "ENG.ORDER": _order,
    "ENG.SORT": _sort,
    "ENG.WRITE_WORD": _write_word,
    "ENG.DICTATION": _said,
    "ENG.MARK_WORDS": _mark,
    "ENG.COPY": _copy,
    "ENG.PUNCTUATE": _punctuate,
    "ENG.CORRECT": _correct,
    "ENG.TABLE": _table,
}


# — the words: British spelling, the school's words ——————————————————————————————————————————————————————————————


def _texts(s: Sample) -> list[tuple[str, str]]:
    """(field, text) for every text a child sees or a marker reads, but the likely wrong answers (misspelt on purpose)
    and the sentence a child corrects."""
    wrong = {w.get("answer") for w in s.get("wrong") or []}
    out = [("ask", s.get("ask") or "")]
    if s["question_type"] != "ENG.CORRECT":
        out.append(("text", s.get("text") or ""))
    out += [("answer", x) for x in flat(s.get("answer"))]
    out += [("accept", x) for x in s.get("accept") or []]
    out += [("key_points", x) for x in s.get("key_points") or []]
    out += [("options", x) for x in flat(s.get("options")) if x not in wrong]
    return out


def _words(s: Sample, c: Context) -> Faults:
    f: Faults = {}
    nots = s.get("not_words") or []
    for where, text in _texts(s):
        lowered = where == "text" and s["question_type"] == "ENG.PUNCTUATE"
        for w in ew.misspelt(text, [] if where == "key_points" else nots, lowered):
            f.setdefault(where, []).append(f"{ew.quoted(w)} is not a word British English spells that way.")
    for where, text in [*_texts(s), ("passage", c.passage)]:
        for w in school_words.found(text):
            f.setdefault(where, []).append(
                f'{ew.quoted(w)}: the school says "regroup" or "exchange", never "carry" or "borrow".'
            )
    return f


def _passage_words(c: Context) -> Faults:
    f: Faults = {}
    for w in ew.misspelt(c.passage):
        f.setdefault("passage", []).append(f"{ew.quoted(w)} is not a word British English spells that way.")
    return f


def _open(s: Sample, c: Context) -> Faults:
    f: Faults = {}
    if s.get("rubric_code") not in c.rubrics:
        f["rubric"] = ["A person reads every answer of this kind: choose what they read it against."]
    if not [k for k in s.get("key_points") or [] if k.strip()]:
        f["key_points"] = ["Say what a right answer does, one line each."]
    if not isinstance(s.get("answer"), str) or not s["answer"].strip():
        f["answer"] = ["Write an example of a right answer."]
    return f


# — the level's own rule ——————————————————————————————————————————————————————————————————————————————————————


def _rule(s: Sample, c: Context) -> Faults:
    r, q, f = c.rule, s["question_type"], {}
    ans, opts = s.get("answer"), s.get("options")
    targets = [x for x in flat(list(ans.values()) if isinstance(ans, dict) else ans) if isinstance(x, str)]

    def within(where: str, what: str, n: int, rng: list[int]) -> None:
        if not rng[0] <= n <= rng[1]:
            says = f"{rng[0]}" if rng[0] == rng[1] else f"{rng[0]} to {rng[1]}"
            f.setdefault(where, []).append(f"This level asks for {says} {what}; this has {n}.")

    if "passage_words" in r:
        within("passage", "words in the passage", len(ew.words(c.passage)), r["passage_words"])
    if "text_words" in r:
        within("text", "words in the sentence", len(ew.words(s.get("text"))), r["text_words"])
    if "answer_letters" in r:
        for w in targets:
            within("answer", f"letters in {ew.quoted(w)}", len(ew.letters(w)), r["answer_letters"])
    if "answer_words" in r:
        within("answer", "words in the right answer", len(ew.words(" ".join(targets))), r["answer_words"])
    if "options" in r and q in ("ENG.CHOOSE", "ENG.GAP") and opts:
        within("options", "options", len(opts), [r["options"], r["options"]])
    if "items" in r and isinstance(opts, list):
        within("options", "items", len(opts), r["items"])
    return _merge(f, _rule_words(s, c, targets))


def _rule_words(s: Sample, c: Context, targets: list[str]) -> Faults:
    r, q, f = c.rule, s["question_type"], {}
    if "pattern" in r and not c.open:
        for w in targets:
            if not re.search(r["pattern"], ew.plain(w)):
                f.setdefault("answer", []).append(
                    f"{ew.quoted(w)} does not show the spelling pattern this level practises."
                )
    if "answer_from" in r:
        allowed = {ew.plain(x) for x in r["answer_from"]}
        if not any(
            ew.plain(w) in allowed or any(re.search(rf"\b{re.escape(a)}\b", ew.plain(w)) for a in allowed)
            for w in targets
        ):
            f.setdefault("answer", []).append(
                f"The right answer uses none of this level's words: {', '.join(r['answer_from'])}."
            )
    if r.get("answer_in_passage") and (not c.passage or not all(ew.found(w, c.passage) for w in targets)):
        f.setdefault("answer", []).append("This level's right answer is words of the passage.")
    if "errors" in r and q == "ENG.CORRECT":
        n, (lo, hi) = ew.corrections(s.get("text") or "", s.get("answer") or ""), r["errors"]
        if not lo <= n <= hi:
            f.setdefault("text", []).append(
                f"This level asks for {lo} to {hi} mistakes to correct; this has {n}."
            )
    if (
        "marks" in r
        and q == "ENG.PUNCTUATE"
        and (missing := [m for m in r["marks"] if m not in (s.get("answer") or "")])
    ):
        f.setdefault("answer", []).append(f"This level's punctuated sentence uses {' '.join(missing)}.")
    return f


def _merge(*parts: Faults) -> Faults:
    out: Faults = {}
    for p in parts:
        for k, v in p.items():
            out.setdefault(k, []).extend(x for x in v if x not in out.get(k, []))
    return out


def faults(s: Sample, c: Context) -> Faults:
    """Everything wrong with a sample, by the field it is in, in words a person reads; {} when it may be stored."""
    q = s["question_type"]
    if not (s.get("ask") or "").strip():
        return {"ask": ["Write what the child is told to do."]}
    if s.get("answer") in (None, "", [], {}):
        return {"answer": ["Write the right answer."]}
    shape = _open(s, c) if c.open else SHAPES.get(q, _said)(s, c)
    if shape:
        return shape
    return _merge(english_wrong.check(s, c), _words(s, c), _passage_words(c), _rule(s, c))
