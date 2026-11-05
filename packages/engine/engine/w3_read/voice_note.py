"""A K2 spoken note read by code into a draft (task M1-01, goals/m1-01-voice-intake.yaml).

After an activity the educator says, in order: "Activity" and its number; "Above:", "Below:", "Not willing:",
"Absent:", each followed by children's roll numbers; "The rest did as expected" if it is true; then, optionally, one
thing she saw, with no heading. The day's first note starts with the date. An incident is a note of its own that starts
with the word "Incident"; it is never read for lists and never becomes evidence.

This reads the transcript's words into one draft line per section, each keeping the words it came from, so Confirm can
show the two side by side. Code reads it, never a model. Where a word cannot be read the line says "could not read" and
Confirm is blocked; a number is never guessed. Every word listened for is a row (`supabase/seed/voice_template.json`,
rule 1). Numbers are matched to children elsewhere, against the day's enrolment.
"""

import re
from dataclasses import dataclass, field
from functools import cache

from engine.core import settings
from engine.w3_read import voice_day

# A word is anything between spaces and punctuation, in any script; the danda (।) ends a Hindi sentence.
WORD = re.compile(r"[^\s,.;:!?।|\-–—\"“”'‘’()\[\]/]+")
SENTENCE_END = re.compile(r"[.!?।]")


@dataclass(frozen=True)
class Token:
    word: str  # lower-cased, as matched against the template
    start: int  # where it sits in the transcript, so a line can show its own words
    end: int


@dataclass(frozen=True)
class Line:
    section: str  # activity, above, below, not_willing, absent, rest, sentence, incident
    words: str  # the transcript's words this line was read from
    numbers: tuple[int, ...] = ()
    text: str | None = None
    said: bool = False  # for "the rest did as expected"
    problems: tuple[str, ...] = ()  # any problem blocks Confirm
    notes: tuple[str, ...] = ()  # what the reader did that the educator should see (a correction, a repeat)


@dataclass(frozen=True)
class Draft:
    transcript: str
    lines: tuple[Line, ...]
    problems: tuple[str, ...] = ()  # problems of the note as a whole
    kind: str = "observation"  # or "incident": a note that starts with "Incident" goes to the incident ledger
    day: tuple | None = (
        None  # the day she said: ("today",), ("yesterday",), ("weekday", 0-6), ("date", day, month)
    )
    # those of `problems` about the date she said: fixed by picking the date
    day_problems: tuple[str, ...] = ()

    def expected_level(self, tpl: "Template") -> int:
        """The level she said she expected, or the template's default when she said none."""
        line = self.line("level")
        return line.numbers[0] if line and len(line.numbers) == 1 else tpl.default_level

    @property
    def blocked(self) -> bool:
        return bool(self.problems) or any(line.problems for line in self.lines)

    def line(self, section: str) -> Line | None:
        return next((x for x in self.lines if x.section == section), None)


@dataclass
class Template:
    sections: dict[str, str]  # code → kind (number, numbers, flag, sentence, incident)
    names: dict[str, str]  # code → the words a problem names it by
    outcomes: dict[str, str | None]  # code → the outcome its children get
    phrases: list[tuple[tuple[str, ...], str]]  # (words, section code), longest first
    filler: set[str]
    none: list[tuple[str, ...]]
    correction: list[tuple[str, ...]]
    numbers: dict[str, int]
    tens: dict[str, int]
    units: dict[str, int]
    days: voice_day.Days
    levels: tuple[int, ...]  # the levels she may say
    default_level: int  # the level expected when she says none (a row; unverified)
    order: list[str] = field(default_factory=list)


def _split(phrase: str) -> tuple[str, ...]:
    return tuple(m.group(0).lower() for m in WORD.finditer(phrase))


def _longest_first(phrases: list[tuple[str, ...]]) -> list[tuple[str, ...]]:
    return sorted(phrases, key=len, reverse=True)


def template_from(rows: dict) -> Template:
    """The template from its rows (the seed's `template`)."""
    phrases = [(_split(w), s["code"]) for s in rows["sections"] for w in s["words"]]
    days = rows["days"]
    return Template(
        sections={s["code"]: s["kind"] for s in rows["sections"]},
        names={s["code"]: s["name"] for s in rows["sections"]},
        outcomes={s["code"]: s["outcome"] for s in rows["sections"]},
        phrases=sorted(phrases, key=lambda p: len(p[0]), reverse=True),
        filler=set(rows["filler"]),
        none=_longest_first([_split(w) for w in rows["none"]]),
        correction=_longest_first([_split(w) for w in rows["correction"]]),
        numbers={_split(w)[0]: int(n) for n, words in rows["number_words"].items() for w in words},
        tens=dict(rows["english_tens"]),
        units=dict(rows["english_units"]),
        days=voice_day.Days.from_rows(days, set(rows["filler"])),
        levels=tuple(rows["levels"]["said"]),
        default_level=rows["levels"]["default_expected"],
        order=[s["code"] for s in rows["sections"]],
    )


@cache
def template() -> Template:
    return template_from(settings.seed("voice_template.json", "template"))


def tokens(transcript: str) -> list[Token]:
    return [Token(m.group(0).lower(), m.start(), m.end()) for m in WORD.finditer(transcript)]


def _starts(toks: list[Token], i: int, phrases: list[tuple[str, ...]]) -> int:
    """→ how many words of the longest phrase that starts at i, or 0."""
    for p in phrases:
        if tuple(t.word for t in toks[i : i + len(p)]) == p:
            return len(p)
    return 0


def _heading(toks: list[Token], i: int, tpl: Template) -> tuple[str, int] | None:
    for words, code in tpl.phrases:
        if tuple(t.word for t in toks[i : i + len(words)]) == words:
            return code, len(words)
    return None


Segment = tuple[str, int, int, list[Token]]  # section, where its heading starts and ends, the words after it


def _segments(toks: list[Token], tpl: Template) -> tuple[list[Token], list[Segment]]:
    """→ the words before any heading, and each section's segment. An incident runs to the end of the note."""
    before: list[Token] = []
    segs: list[Segment] = []
    i = 0
    while i < len(toks):
        in_incident = bool(segs) and tpl.sections[segs[-1][0]] == "incident"
        hit = None if in_incident else _heading(toks, i, tpl)
        if hit:
            segs.append((hit[0], toks[i].start, toks[i + hit[1] - 1].end, []))
            i += hit[1]
            continue
        (segs[-1][3] if segs else before).append(toks[i])
        i += 1
    return before, segs


def _number_at(toks: list[Token], i: int, tpl: Template) -> tuple[int, int] | None:
    """→ (number, words used) if a number is said at i: digits in any script, a number word in English or Hindi,
    or an English "twenty one". "one seven" is two numbers, never seventeen."""
    w = toks[i].word
    if w.isdecimal():
        return int(w), 1
    if w in tpl.tens and i + 1 < len(toks) and toks[i + 1].word in tpl.units:
        return tpl.tens[w] + tpl.units[toks[i + 1].word], 2
    if w in tpl.numbers:
        return tpl.numbers[w], 1
    return None


@dataclass
class _Heard:
    numbers: list[int] = field(default_factory=list)
    unread: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    none: bool = False
    correcting: bool = False

    def add(self, n: int) -> None:
        if self.correcting and self.numbers:
            self.notes.append(f"{self.numbers[-1]} corrected to {n}")
            self.numbers[-1] = n
        elif n in self.numbers:
            self.notes.append(f"{n} said more than once")
        else:
            self.numbers.append(n)
        self.correcting = False


def _hear(toks: list[Token], tpl: Template, text: str) -> _Heard:
    heard = _Heard()
    i = 0
    while i < len(toks):
        if used := _starts(toks, i, tpl.none):
            heard.none = True
        elif used := _starts(toks, i, tpl.correction):
            heard.correcting = bool(heard.numbers)
        elif hit := _number_at(toks, i, tpl):
            heard.add(hit[0])
            used = hit[1]
        else:
            if toks[i].word not in tpl.filler:
                heard.unread.append(text[toks[i].start : toks[i].end])
            used = 1
        i += used
    return heard


def _problems_of(heard: _Heard, kind: str) -> list[str]:
    out = [f"could not read '{w}'" for w in heard.unread]
    if heard.correcting:
        out.append("a correction with no number after it")
    if heard.none and heard.numbers:
        out.append("said none, and numbers too")
    if not heard.numbers and not heard.none and not heard.unread:
        out.append("could not read: no number heard")
    if kind == "number" and len(heard.numbers) > 1:
        out.append("one number expected, heard " + ", ".join(map(str, heard.numbers)))
    return out


def _sentences(toks: list[Token], text: str) -> list[list[Token]]:
    """The words cut where the transcript ends a sentence (. ! ? ।)."""
    out: list[list[Token]] = []
    for k, t in enumerate(toks):
        if not out or SENTENCE_END.search(text[toks[k - 1].end : t.start]):
            out.append([])
        out[-1].append(t)
    return out


def _cut_sentence(seg: Segment, text: str, tpl: Template) -> tuple[Segment, list[Token]]:
    """The last section's words → (the section's own, the free sentence after them). After "the rest did as
    expected" every word is the sentence; after a list, the first sentence holding a word that is not a number
    starts it. Without a full stop between them the sentence is "could not read", never guessed."""
    code, start, head_end, toks = seg
    if tpl.sections[code] == "flag":
        return (code, start, head_end, []), toks
    groups = _sentences(toks, text)
    for k, group in enumerate(groups[1:], start=1):
        if _hear(group, tpl, text).unread:
            own = [t for g in groups[:k] for t in g]
            return (code, start, head_end, own), [t for g in groups[k:] for t in g]
    return seg, []


def _span(toks: list[Token], text: str) -> str:
    return text[toks[0].start : toks[-1].end] if toks else ""


def _line(seg: Segment, kind: str, text: str, tpl: Template) -> Line:
    section, start, head_end, toks = seg
    words = text[start : toks[-1].end if toks else head_end]
    if kind == "incident":
        body = _span(toks, text)
        return Line(
            section, words, text=body, problems=() if body else ("could not read: nothing said after it",)
        )
    if kind == "flag":
        extra = [text[t.start : t.end] for t in toks if t.word not in tpl.filler]
        return Line(section, words, said=True, problems=tuple(f"could not read '{w}'" for w in extra))
    heard = _hear(toks, tpl, text)
    return Line(
        section,
        words,
        tuple(heard.numbers),
        problems=tuple(_problems_of(heard, kind)),
        notes=tuple(heard.notes),
    )


def _merge(a: Line, b: Line, name: str) -> Line:
    """The same heading said twice: one line, its numbers together, its words both shown."""
    numbers = a.numbers + tuple(n for n in b.numbers if n not in a.numbers)
    return Line(
        a.section,
        f"{a.words} … {b.words}",
        numbers,
        None,
        a.said or b.said,
        a.problems + b.problems,
        a.notes + b.notes + (f"'{name}' said twice: read together",),
    )


def _cross_checks(lines: dict[str, Line], tpl: Template) -> list[str]:
    out = [] if "activity" in lines else ["could not read: no activity number"]
    level = lines.get("level")
    if level and level.numbers and level.numbers[0] not in tpl.levels:
        out.append(f"level {level.numbers[0]} is not a level ({', '.join(map(str, tpl.levels))})")
    seen: dict[int, str] = {}
    for code in (c for c in tpl.order if tpl.sections[c] == "numbers"):
        for n in lines[code].numbers if code in lines else ():
            if n in seen:
                out.append(f"{n} is in both {tpl.names[seen[n]]} and {tpl.names[code]}")
            seen.setdefault(n, code)
    return out


def read(transcript: str, tpl: Template | None = None) -> Draft:
    """The transcript read into a draft. Nothing in it is ticked: the educator confirms or corrects every line."""
    tpl = tpl or template()
    before, segs = _segments(tokens(transcript), tpl)
    day, problems = voice_day.read_day([(t.word, transcript[t.start : t.end]) for t in before], tpl.days)
    if segs and tpl.sections[segs[0][0]] == "incident":
        return Draft(
            transcript,
            (_line(segs[0], "incident", transcript, tpl),),
            tuple(problems),
            "incident",
            day,
            tuple(problems),
        )
    sentence: list[Token] = []
    if segs and tpl.sections[segs[-1][0]] != "incident":
        segs[-1], sentence = _cut_sentence(segs[-1], transcript, tpl)
    lines: dict[str, Line] = {}
    for seg in segs:
        code = seg[0]
        new = _line(seg, tpl.sections[code], transcript, tpl)
        lines[code] = _merge(lines[code], new, tpl.names[code]) if code in lines else new
    if sentence:
        lines["sentence"] = Line("sentence", _span(sentence, transcript), text=_span(sentence, transcript))
    if "incident" in lines:
        inc = lines["incident"]
        lines["incident"] = Line(
            inc.section,
            inc.words,
            text=inc.text,
            problems=inc.problems,
            notes=("an incident is a note of its own: these words are kept apart, never evidence",),
        )
    day_problems = tuple(problems)
    problems += _cross_checks(lines, tpl)
    return Draft(
        transcript,
        tuple(lines[c] for c in tpl.order if c in lines),
        tuple(problems),
        "observation",
        day,
        day_problems,
    )
