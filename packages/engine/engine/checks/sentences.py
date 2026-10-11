"""A printed sentence worked out by itself, as the child reads it (goals/md4b2-equality.yaml).

The scenarios' check (`scenarios._answer_is_right`) hands a box's or a tick's sentence here: whole numbers, + − × ÷ and
brackets, = between sides, ○ or □ between two sides compared, □ for what is missing. It is worked exactly, × and ÷
before + and −, apart from the code that wrote it:

- `printed`: the question's own sentence, its text or a balance's two pans;
- `box`: the one whole number every □ of a sentence stands for: "6 × 8 = 8 × □" is 6, "□ + 7 = 21 − □" is 7, "48 ÷ □ =
  24" is 2, and "12 × 5 = 60, so 12 × 10 = □" is 120 once 12 × 5 is 60;
- `ticks`: each tick's answer from its own sentence, or from the question's where its label is no sentence ("the
  sign"): the signs that make it true, <, = or > between its two sides, true or false.

A side divided by 0 has no value, so "9 ÷ 0 = 0" is false. A sentence no single answer makes true is worked out as
having none (`NO_ONE_ANSWER`), never skipped: a question with no answer, or two, is wrong. A sentence this cannot read
— a word, a digit in a box — is left to the other checks (None)."""

import itertools
import re
from fractions import Fraction
from typing import Any

NO_ONE_ANSWER = -1  # no box holds it: a sentence no single whole number makes true
NOT_ONE = "no single answer"  # no tick is it: two signs fit, or none
SIGNS = {"+", "−", "-", "×", "÷"}
_TOKEN = re.compile(r"\s*(?:(\d+)|(□)|([+−×÷()-]))")


class Unreadable(ValueError):
    """Not a sentence of numbers and signs."""


def _tokens(text: str) -> list[str]:
    out: list[str] = []
    i, text = 0, text.strip()
    while i < len(text):
        m = _TOKEN.match(text, i)
        if not m:
            raise Unreadable(text)
        out.append(m.group(1) or m.group(2) or m.group(3))
        i = m.end()
    if not out:
        raise Unreadable(text)
    return out


class _Side:
    """One side of a sentence, worked with □ as `x`: None where it divides by 0."""

    def __init__(self, text: str, x: Fraction) -> None:
        self.t, self.i, self.x = _tokens(text), 0, x

    def value(self) -> Fraction | None:
        v = self._sum()
        if self.i != len(self.t):
            raise Unreadable(" ".join(self.t))
        return v

    def _next(self) -> str | None:
        return self.t[self.i] if self.i < len(self.t) else None

    def _sum(self) -> Fraction | None:
        v = self._product()
        while self._next() in ("+", "−", "-"):
            op = self.t[self.i]
            self.i += 1
            w = self._product()
            v = None if v is None or w is None else v + w if op == "+" else v - w
        return v

    def _product(self) -> Fraction | None:
        v = self._number()
        while self._next() in ("×", "÷"):
            op = self.t[self.i]
            self.i += 1
            w = self._number()
            v = None if v is None or w is None or (op == "÷" and w == 0) else v * w if op == "×" else v / w
        return v

    def _number(self) -> Fraction | None:
        tok = self._next()
        self.i += 1
        if tok == "(":
            v = self._sum()
            if self._next() != ")":
                raise Unreadable(" ".join(self.t))
            self.i += 1
            return v
        if tok == "□":
            return self.x
        if tok is not None and tok.isdigit():
            return Fraction(int(tok))
        raise Unreadable(" ".join(self.t))


def _sides(sentence: str, x: Fraction) -> list[Fraction | None]:
    parts = sentence.split("=")
    if len(parts) < 2:
        raise Unreadable(sentence)
    return [_Side(p, x).value() for p in parts]


def _holds(sentence: str, x: Fraction = Fraction(0)) -> bool:
    """Every side the same number; a side with none (÷ 0) holds nothing. Raises Unreadable."""
    sides = _sides(sentence, x)
    return None not in sides and len(set(sides)) == 1


def _clauses(text: str) -> list[str]:
    return [c.strip() for c in re.split(r",\s*so\s+|\s+and\s+", text.strip()) if c.strip()]


def _numbers(text: str) -> list[int]:
    return [int(n) for n in re.findall(r"\d+", text)]


def _solve(sentence: str) -> int:
    """The one whole number □ stands for: worked straight back where every side is a line in □ (the box multiplied, added
    or taken away), else tried from 0 to past the sentence's largest number (the box a divisor)."""
    at = [_sides(sentence, Fraction(x)) for x in (0, 1, 2)]
    lines = [[v for v in sides if v is not None] for sides in at]
    if all(len(vs) == len(at[0]) for vs in lines) and all(
        c - b == b - a for a, b, c in zip(*lines, strict=True)
    ):
        start, slope = lines[0], [b - a for a, b in zip(lines[0], lines[1], strict=True)]
        fits = {
            -(start[i] - start[0]) / (slope[i] - slope[0])
            for i in range(1, len(start))
            if slope[i] != slope[0]
        }
        if len(fits) != 1:
            return NO_ONE_ANSWER  # □ cancels out (every number fits, or none) or two sides want two numbers
        x = fits.pop()
        return int(x) if x.denominator == 1 and x >= 0 and _holds(sentence, x) else NO_ONE_ANSWER
    fits = [x for x in range(0, max(_numbers(sentence), default=0) + 2) if _holds(sentence, Fraction(x))]
    return fits[0] if len(fits) == 1 else NO_ONE_ANSWER


def box(text: str) -> int | None:
    """The one whole number the □ of a printed sentence stands for, any sentence given before it (", so") true too;
    `NO_ONE_ANSWER` where none or several do; None for a sentence this cannot read, or one asking more than one box."""
    clauses = _clauses(text)
    asked = [c for c in clauses if "□" in c]
    if len(asked) != 1 or "=" not in asked[0]:
        return None
    try:
        given = [_holds(c) for c in clauses if "□" not in c]
        return _solve(asked[0]) if all(given) else NO_ONE_ANSWER
    except Unreadable:
        return None


def _fill(sentence: str, signs: tuple[str, ...]) -> str:
    """The sentence with each □ a sign, in the order printed."""
    parts = sentence.split("□")
    return "".join(p + sign for p, sign in zip(parts, [*signs, ""], strict=True))


def _want(sentence: str, options: list[str], k: int) -> str | None:
    """The tick a sentence asks: the k-th of the only signs that make it true, <, = or > between its two sides, or true
    or false; None for options or a sentence this cannot read."""
    if options and set(options) <= SIGNS:
        n = sentence.count("□")
        if k >= n:
            return None
        fits = [signs for signs in itertools.product(options, repeat=n) if _holds(_fill(sentence, signs))]
        return fits[0][k] if len(fits) == 1 else NOT_ONE
    if set(options) == {"<", "=", ">"}:
        parts = re.split(r"[○□]", sentence)
        if len(parts) != 2:
            return None
        left, right = (_Side(p, Fraction(0)).value() for p in parts)
        if left is None or right is None:
            return NOT_ONE
        return "<" if left < right else ">" if left > right else "="
    if sorted(options) == ["false", "true"]:
        return "true" if _holds(sentence) else "false"
    return None


def printed(spec: dict[str, Any]) -> str:
    """The question's own sentence: its text, or a balance's two pans read as one ("19 + 24 = □ + 13")."""
    left, right = spec.get("left"), spec.get("right")
    if isinstance(left, list) and isinstance(right, list):
        pans: list[list[Any]] = [left, right]
        return " = ".join(" + ".join("□" if n is None else str(n) for n in pan) for pan in pans)
    return str(spec.get("text") or "")


def ticks(spec: dict[str, Any], responses: list[Any], stated: dict[str, str]) -> list[bool]:
    """Each sign, comparison or true-or-false tick against the one its sentence asks: its own label where that is a
    sentence (numbers and = or ○), else the question's (`spec["text"]`), its signs in the order they are printed. Every
    other tick is left to the checks that know it."""
    text, out, k = printed(spec), [], 0
    for r in responses:
        if r.kind != "tick" or r.rid not in stated:
            continue
        label = r.label or ""
        own = bool(re.search(r"\d", label) and re.search(r"[=○]", label))
        shared = not own and set(r.options) <= SIGNS
        try:
            want = _want(label if own else text, list(r.options), k if shared else 0)
        except Unreadable:
            want = None
        k += shared
        if want is not None:
            out.append(stated[r.rid] == want)
    return out
