"""The parent report's words held to their facts (goals/w4c-parent-report.yaml, `parent_report.py`): each skill and
mistake answered once, no number the facts do not hold however it is written, no name, no code, no bracket but [child],
no time the facts do not give, none of the words the school does not use. What the check refuses, and why, is each
thing a person found reading the drafts on live (2026-09-28, v1-v6).
"""

import json
import re

# every form a parent could read: "problems" slipped past "problem" on the first eval (2026-09-28)
BANNED = (
    r"teachers?",
    r"borrow\w*",
    r"weak\w*",
    r"poor\w*",
    r"behind",
    r"struggl\w*",
    r"concerns?\w*",
    r"fail\w*",
    r"lend\w*",  # v7: "rewrite the lender digit" — the borrowing picture; the school's word is exchange
)
# a skill's state is said on its own line, held there to the list it is in; v7's summary called a skill that was only
# improving "now secure", which no check could hold the summary to
NEARLY = re.compile(r"\b(nearly|almost|not yet)\b", re.IGNORECASE)
# v10: "has mastered two-digit subtraction", said of a skill only improving — mastery is a state as secure is
# v11: "is ready to move forward in most areas" — whether a child moves on is the engine's plan, on the page
SECURE = re.compile(r"\b(secure(ly)?|master(s|ed|y|ing)?|ready (to|for))\b", re.IGNORECASE)
# the facts give the dates and the days the answers cover; "this week" was a model's guess at them (v3's first eval)
# v8: "earlier in the month" — any calendar span said of the answers is a guess at them
WHEN = re.compile(
    r"\b(this|last|next|the) (week|month|term|year)\b|\b(today|yesterday|weekly|monthly)\b", re.IGNORECASE
)
# a school in Pune: v8 had a parent use "ten-pence and one-penny coins"
MONEY = re.compile(r"\b(pence|penny|pennies|pounds?|dollars?|cents?|euros?)\b", re.IGNORECASE)
# "4 of 4", "two of three", "five of the last eight": a count said of a skill is that skill's own (v8 gave one child's
# two skills the same "10 of 11", and the numbers were in the facts, so nothing caught it)
PAIR = re.compile(
    # v10: "one correct answer out of four" is a count as "1 of 4" is
    r"\b([a-z]+(?:-[a-z]+)?|\d+) (?:(?:correct |right )?answers? )?(?:out )?of "
    r"(?:the (?:first|last|most recent|recent|earlier) )?([a-z]+(?:-[a-z]+)?|\d+)\b",
    re.IGNORECASE,
)
# "problem" said of the child — "has a problem", "problems with" — never the kind of question ("an addition problem",
# v6's second run); a maths problem is not the child's: "word problems" is the skill set's own name, and v6 wrote "story problem" twice.
# The ban is on the word said of the child ("has a problem"), never on the kind of question
SCHOOLS_OWN = re.compile(r"\b(word|story|maths?|one[- ]step|two[- ]step)[- ]problems?\b", re.IGNORECASE)
# r2, v12 on live: "Make a three-digit number with coins (for example, three ten-rupee notes and five one-rupee coins)"
# is thirty-five. What coins make is arithmetic, and code's (ADR 0036): Jev was 0.75 sure the sentence was fine
COINS = re.compile(r"\b([a-z]+(?:-[a-z]+)?|\d+) (hundred|ten|one)-rupee (?:coins?|notes?)\b", re.IGNORECASE)
RUPEES = {"hundred": 100, "ten": 10, "one": 1}
COINS_MAKE = re.compile(
    r"\b(?:make|makes|making|show|shows|showing) ([a-z]+(?:-[a-z]+)?|\d+) with\b", re.IGNORECASE
)
COINS_SIZE = re.compile(r"\b(one|two|three|four)-digit number\b", re.IGNORECASE)
# e10: "Try the kite question beside this together" — the page prints the child's own questions beside the words, and
# no fact holds a kite; Haiku 4.5, Sonnet 5.5 and Opus 5.5 each let it pass (2026-09-29). Which questions the facts
# hold is code's: a question, story or example the words name by what it is about is one the facts hold
NAMED = re.compile(r"\bthe ([a-z]+(?:-[a-z]+)?) (question|story|example)\b", re.IGNORECASE)
NAMES_NOTHING = {"subtraction", "addition", "sum", "full", "whole", "same", "first", "second", "third", "next", "last",
                 "other", "word", "maths", "two-step", "one-step", "harder", "easier", "similar", "new"}  # fmt: skip
# Nimish, 2026-09-29: a skill only improving reads as improving. e7, v12 on live: "[child] can add two 2-digit numbers
# in columns and in a line, carrying exactly when a column needs it." of a skill 11 of 18 right — and the summary,
# unlike a skill's own line, prints no state beside its words
IMPROVED = re.compile(r"\b(improv\w*|grow\w*|grew|better|progress\w*)\b", re.IGNORECASE)
DIGITS = {"one": "1", "two": "2", "three": "3", "four": "4", "five": "5"}
CODE = re.compile(r"\b(M_[A-Z0-9_]+|[RX]\d{1,2}|[A-Z]{2,}\.[A-Z0-9_.]*[A-Z0-9])\b")
PLAIN_CAPS = {"I", "Cornerstone", "School", "Pune", "Grade", "Maths", "Math"}


def _words(text):
    """A text's words as a skill's "can" is compared: lower case, numbers as digits, a plural's or a verb's s off."""
    out = [DIGITS.get(w, w) for w in map(str, re.findall(r"[a-z0-9]+", text.lower()))]
    return [w[:-1] if len(w) > 3 and w.endswith("s") and not w.endswith("ss") else w for w in out]


def _names(text, skill):
    """Whether a text names a skill by what it can do: the first words of its "can", up to its first comma."""
    want, got = _words(skill["can"].split(",")[0])[:5], _words(text)
    return any(got[i : i + len(want)] == want for i in range(len(got) - len(want) + 1))


def _texts(d):
    return [d["summary"], *(c["sentence"] for c in d["can_do"]), *(w["explanation"] for w in d["working_on"]),
            *d["at_home"], d.get("next_at_school", "")]  # fmt: skip


UNITS = {w: i for i, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen"
    " eighteen nineteen".split())}  # fmt: skip
TENS = {
    w: 10 * i
    for i, w in enumerate("_ _ twenty thirty forty fifty sixty seventy eighty ninety".split())
    if i > 1
}
SCALES = {"hundred": 100, "thousand": 1000}


def _count(token):
    """A count written in digits or in words ("seven", "twenty-one", "none"); None when the word is not a number."""
    t = token.lower()
    if t.isdigit():
        return int(t)
    if t == "none":
        return 0
    parts = t.split("-")
    vals = [v for w in parts if (v := UNITS.get(w, TENS.get(w))) is not None]
    return sum(vals) if len(vals) == len(parts) else None


def _pairs(text):
    return {
        (a, b) for x, y in PAIR.findall(text) if (a := _count(x)) is not None and (b := _count(y)) is not None
    }


def numbers_in(text):
    """(values written in digits, values written in words) — "9,000" is 9000, "sixty-one" 61, "nine thousand four
    hundred" 9400. A bare "a hundred" or "hundreds" is the place value's name, not a count, and is not a value.
    v4 on live wrote a child's example in words ("leaving sixty-one") where no digit check could see it."""
    digits = {int(n.replace(",", "")) for n in re.findall(r"\d{1,3}(?:,\d{3})+|\d+", text)}
    words, total, cur = set(), None, None

    def flush():
        if total is not None or cur is not None:
            words.add((total or 0) + (cur or 0))

    # words build a number only as English does: "twenty" then "three" is 23, but "ten, twenty, thirty" is three
    # numbers and "one ten, two tens" is not 13 (v5 on live read them as 60 and 13); any other token ends a number
    for w in re.findall(r"[a-z]+|[^a-z\s]", text.lower().replace("-", " ")) + ["."]:
        v = UNITS.get(w, TENS.get(w))
        tail = cur % 100 if cur is not None else 0
        if v is not None:
            joins = cur is not None and (
                tail == 0 or (w in UNITS and v < 10 and tail >= 20 and tail % 10 == 0)
            )
            if cur is not None and not joins:
                flush()
                total = None
            cur = (cur if cur is not None and joins else 0) + v
        elif w in SCALES and cur is not None:
            cur *= SCALES[w]
            if w == "thousand":
                total, cur = (total or 0) + cur, 0
        elif w == "and" and cur is not None:
            continue
        else:
            flush()
            total = cur = None
    return digits, words


def _coins(t):
    """What the coins a sentence counts out make, where the sentence says they make something else: [] when they agree,
    or when it counts no coins ("use ten-rupee coins" is advice, not an amount)."""
    counted = [(n, RUPEES[kind.lower()]) for x, kind in COINS.findall(t) if (n := _count(x)) is not None]
    if not counted:
        return []
    made = sum(n * r for n, r in counted)
    said = COINS_MAKE.search(t)
    if said and _count(said.group(1)) not in (None, made):
        return [f"the coins make {made}, not {said.group(1)}: {t!r}"]
    size = COINS_SIZE.search(t)
    if size and UNITS[size.group(1).lower()] != len(str(made)):
        return [f"the coins make {made}, which is not a {size.group(0)}: {t!r}"]
    return []


def check(f, d):
    """What the words say that the facts do not, or that the school does not say — [] when nothing."""
    problems = []
    want = [x["id"] for k in ("can_do", "nearly", "improving") for x in f[k]]
    got = [c["id"] for c in d["can_do"]]
    if sorted(got) != sorted(want):
        problems.append(f"can_do must have exactly one entry for each of {want}; it has {got}")
    want, got = [w["id"] for w in f["working_on"]], [w["id"] for w in d["working_on"]]
    if sorted(got) != sorted(want):
        problems.append(f"working_on must have exactly one entry for each of {want}; it has {got}")
    if "[child]" not in d["summary"]:
        problems.append("the summary never says [child]")
    # a skill's count and its state are code's, printed beside its line: v9 said "6 of 6" of a skill that was 4 of 4,
    # three tries running, and v7's summary called an improving skill "now secure". The words say what the child can
    # do; the page says how many and how sure
    for where, t in [("the summary", d["summary"])] + [
        (f"{c['id']}'s line", c["sentence"]) for c in d["can_do"]
    ]:
        for m in PAIR.finditer(t):
            if _pairs(m.group(0)):
                problems.append(
                    f"{where} gives the count {m.group(0)!r}; the page prints every count, so take it out"
                )
        said = SECURE.search(t) or (where != "the summary" and NEARLY.search(t))
        if said:
            problems.append(
                f"{where} says {said.group(0)!r}; the page shows how secure a skill is, so take it out"
            )
    for said in re.split(r"(?<=[.!?])\s+(?=[A-Z\[])", d["summary"]):
        for x in f["improving"]:
            if _names(said, x) and not IMPROVED.search(said):
                problems.append(
                    f"the summary says what {x['id']} is without saying it has improved; it is only improving: {said!r}"
                )
    known = json.dumps(f, ensure_ascii=False)
    # the dates head the letter; their digits (2026, 09, 25) are not numbers the words may use
    held = numbers_in(json.dumps({k: v for k, v in f.items() if k not in ("from", "to")}, ensure_ascii=False))
    numbers = held[0] | held[1]
    words = set(re.findall(r"[A-Za-z]+", known)) | PLAIN_CAPS
    for t in _texts(d):
        digits, spelled = numbers_in(t)
        # counting in tens aloud ("ten, twenty, thirty"), "a hundred", "a thousand" is the words of counting, not a
        # count of the child's; any other number over ten said in words is a claim, and must be in the facts
        counting = {v for v in spelled if (v <= 100 and v % 10 == 0) or v == 1000}
        for n in sorted(digits - numbers) + sorted(v for v in spelled - numbers - counting if v > 10):
            problems.append(f"the number {n} is not in the facts: {t!r}")
        said_of = r"\b(has|have|having|had)\s+(a\s+|some\s+)?problems?\b|\bproblems?\s+(with|in)\b"
        if m := re.search(said_of, SCHOOLS_OWN.sub("", t), re.IGNORECASE):
            problems.append(f"the word {m.group(0)!r} is not the school's: {t!r}")
        for w in BANNED:
            if m := re.search(rf"\b{w}\b", SCHOOLS_OWN.sub("", t), re.IGNORECASE):
                problems.append(f"the word {m.group(0)!r} is not the school's: {t!r}")
        if m := WHEN.search(t):
            problems.append(f"a time the facts do not give, {m.group(0)!r}: {t!r}")
        if m := MONEY.search(t):
            problems.append(f"money the school's parents do not use, {m.group(0)!r}: {t!r}")
        if "%" in t or re.search(r"\bper ?cent", t, re.IGNORECASE):
            problems.append(f"a percentage: {t!r}")
        if "!" in t:
            problems.append(f"an exclamation mark: {t!r}")
        problems += _coins(t)
        for m in NAMED.finditer(t):
            if m.group(1).lower() not in NAMES_NOTHING and m.group(1).lower() not in known.lower():
                problems.append(f"{m.group(0)!r} is not one of [child]'s own questions: {t!r}")
        if m := CODE.search(t):
            problems.append(f"a code, {m.group(0)}: {t!r}")
        if re.search(r"[\[\]]", t.replace("[child]", "")):  # "[child become" printed as it stood (v5)
            problems.append(f"a bracket other than [child]: {t!r}")
        plain = t.replace("[child]", "")
        for m in re.finditer(r"\b[A-Z][a-z]+\b", plain):
            before = re.sub(r"[\s'\"‘’“”()\-—]+$", "", plain[: m.start()])
            # a sentence's first word: after a full stop (a closing quote between), or opening a quoted sentence
            opens = re.search(r"['\"‘“]$", plain[: m.start()].rstrip())
            starts = not before or before[-1] in ".!?:;" or bool(opens)
            if not starts and m.group(0) not in words:
                problems.append(f"{m.group(0)!r} is a name or word the facts do not hold: {t!r}")
    return problems
