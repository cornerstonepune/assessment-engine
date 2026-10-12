"""Of two story cases the taxonomy tells apart by what a story prints rather than by what it asks, which one a story is
(goals/md4d2b5-story-told-apart.yaml).

`story_shape` asks Jev to read what is known and what is asked, "not the words it uses" — rightly, for a shape. But two
pairs of cases differ only in what is printed: "each" that means ÷ (B24) is grouping told with "each" or "every", the
word that has a child multiply, and grouping (B03) is the same story without it; a price list (B26) is a price read
from prices set out as a list, and a price (B06) is one told in a sentence. On live (run 38251975489) Jev split 0.54 /
0.46 across the first pair and took both list stories for one price. Which of a pair a story is, is code's to read: the
words are a config row (`story_shape.told_by_words`), the layout is a colon before the prices. Jev's probability for
the pair is then the sum of the two, since code settles between them.
"""

import re
from typing import Any

from engine.core import settings

LIST = "TABLE_OR_CHART"
NUMBER = re.compile(r"\d[\d,]*")
SENTENCE_END = re.compile(r"[.?!](?:\s|$)")


def listed(text: str) -> bool:
    """Whether a story sets its numbers out as a list: a colon, then two numbers or more before that sentence ends
    ("Price list: pen ₹15, eraser ₹5.", "Canteen prices: idli ₹10 a plate, dosa ₹30 a plate.")."""
    _, colon, rest = text.partition(":")
    return bool(colon) and len(NUMBER.findall(SENTENCE_END.split(rest, maxsplit=1)[0])) >= 2


def words(conn: Any) -> dict[str, Any]:
    """{structure: {"instead_of": structure, "words": [...]}}: a case its words name, and the case it is without them."""
    return settings.config(conn, "story_shape.told_by_words", {})


def _without(match: dict[str, Any], key: str) -> dict[str, Any]:
    return {k: v for k, v in match.items() if k != key}


def resolved(told: dict[str, Any], known: dict[str, Any], key: str, text: str) -> str:
    """The option code settles once Jev has chosen `key`: `key` itself, or its twin when the story's layout or words
    say it is the other of the pair."""
    m = known[key]["match"]
    bare = _without(m, "context")
    for k, r in known.items():
        # a list and a price: alike but for how the prices are set out
        if k != key and _without(r["match"], "context") == bare:
            return key if (m.get("context") == LIST) == listed(text) else k
    for named, rule in told.items():
        if m["structure"] not in (named, rule["instead_of"]) or m.get("remainder_use"):
            continue
        says = re.search(rf"\b({'|'.join(map(re.escape, rule['words']))})\b", text, re.IGNORECASE)
        want = named if says else rule["instead_of"]
        return next(
            (
                k
                for k, r in known.items()
                if r["match"]["structure"] == want
                and not r["match"].get("remainder_use")
                and r["match"]["taxonomy"] == m["taxonomy"]
            ),
            key,
        )
    return key


def merged(told: dict[str, Any], known: dict[str, Any], ranked: list[tuple[str, float]], text: str):
    """Jev's ranking over what code settles: each option is the case code reads it as, its probability the sum of the
    options read as it. [(option, p)], best first."""
    total: dict[str, float] = {}
    for option, p in ranked:
        k = resolved(told, known, option, text) if option in known else option
        total[k] = total.get(k, 0.0) + p
    return sorted(total.items(), key=lambda kv: -kv[1])
