"""The words of an English sample, read by code (goals/edt_edit_samples_and_kinds.yaml): how a child's words compare, and
whether every word is spelt as British English spells it. From research/english_rules.py and english_spelling.py, which
checked the seed; the engine now checks what an educator saves with the same rules.

Spelling is read against the en_GB Hunspell dictionary LibreOffice ships, fetched once at a pinned commit into data/
(gitignored) and refused if its fingerprint differs; the Indian English words a Pune classroom uses are a list a person
reads, supabase/seed/english_words.txt. A capitalised word the dictionary does not know is a name (Meera, Kothrud).
"""

import difflib
import functools
import hashlib
import re
import urllib.request
from collections.abc import Iterable

from engine.core import db

WORD = re.compile(r"[A-Za-z0-9]+(?:['’][A-Za-z]+)*")
SPELT = re.compile(r"[A-Za-z]+(?:['’-][A-Za-z]+)*")
COMMIT = "67032ee957631908098a72edf48dc81cac27e369"
SHA256 = {
    "dic": "04e90f34f5263bf26780e9c4a442e9ad16584e227af49ddd1b3b21b01df5b29c",
    "aff": "0fd6ed120ef28957847d98ba5149b117e27116cf81b5aa36208453f6755a36fd",
}
HERE = db.REPO_ROOT / "data" / "dictionaries"
LOCAL = (
    db.REPO_ROOT / "supabase" / "seed" / "english_words.txt"
)  # mounted beside the engine, as every seed is
# American spellings a British paper must not carry, some of which the dictionary also takes (Cambridge writes British)
AMERICAN = {"color", "colors", "colored", "colorful", "favorite", "favorites", "favor", "honor", "neighbor",
            "neighbors", "neighborhood", "behavior", "center", "centers", "theater", "gray", "mom", "moms",
            "organize", "organized", "realize", "realized", "recognize", "apologize", "traveled", "traveling",
            "jewelry", "catalog", "defense", "practicing", "flavor", "humor", "labor", "harbor", "rumor", "odor",
            "vapor", "armor", "meters", "liter", "liters", "airplane", "candies", "cookie", "cookies", "math"}  # fmt: skip


class NoDictionary(Exception):
    """The spelling list could not be read, so nothing is checked and nothing is saved."""


def quoted(x: object) -> str:
    return f"“{x}”"


def words(text: str | None) -> list[str]:
    """The words of a text, an apostrophe kept inside a word (don't, girls')."""
    return WORD.findall(text or "")


def plain(text: str | None) -> str:
    """Lower case, curly apostrophes and quotes straightened, spaces single: for comparing what a child wrote."""
    text = (text or "").replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    return " ".join(text.lower().split())


def letters(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", plain(text))


def found(part: str, text: str | None) -> bool:
    """A phrase in a text, case, curly quotes, spacing and end punctuation ignored."""
    return plain(part).strip(" .,!?;:\"'") in plain(text)


def same_words(a: str | None, b: str | None) -> bool:
    """The same words in the same order, punctuation and case ignored: what punctuating a sentence must keep."""
    return [w.lower() for w in words(a)] == [w.lower() for w in words(b)]


def corrections(text: str, answer: str) -> int:
    """How many words a correction changed, added or took out."""
    a, b = [w.lower() for w in words(text)], [w.lower() for w in words(answer)]
    ops = difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes()
    return sum(max(i2 - i1, j2 - j1) for tag, i1, i2, j1, j2 in ops if tag != "equal")


@functools.cache
def _dictionary():
    from spylls.hunspell import Dictionary

    try:
        HERE.mkdir(parents=True, exist_ok=True)
        for ext, want in SHA256.items():
            path = HERE / f"en_GB.{ext}"
            if not path.exists():
                url = f"https://raw.githubusercontent.com/LibreOffice/dictionaries/{COMMIT}/en/en_GB.{ext}"
                path.write_bytes(urllib.request.urlopen(url, timeout=60).read())  # noqa: S310 (a pinned https address)
            if hashlib.sha256(path.read_bytes()).hexdigest() != want:
                path.unlink()
                raise NoDictionary(f"{path.name} is not the pinned en_GB dictionary")
    except OSError as e:
        raise NoDictionary(str(e)) from e
    return Dictionary.from_files(str(HERE / "en_GB"))


@functools.cache
def _local() -> frozenset[str]:
    lines = LOCAL.read_text().splitlines() if LOCAL.exists() else []
    return frozenset(
        ln.split("—")[0].strip().lower() for ln in lines if ln.strip() and not ln.startswith("#")
    )


@functools.cache
def known(word: str) -> bool:
    return word.lower() in _local() or bool(_dictionary().lookup(word))


def misspelt(text: str | None, not_words: Iterable[str] = (), lowered: bool = False) -> list[str]:
    """Each word of a text that is not British English, once. A word listed as shown on purpose (a misspelling to fix,
    a word part such as -ough) is let through; a capitalised unknown word is a name, unless the text took its capitals
    away on purpose (a sentence to punctuate)."""
    nots, out = {w.lower() for w in not_words}, []
    for raw in SPELT.findall((text or "").replace("’", "'")):
        if raw.lower() in AMERICAN:
            out.append(raw)
            continue
        if known(raw):
            continue
        for w in raw.split("-"):
            w = re.sub(r"'s$|s'$", "", w) if len(w) > 3 else w
            if not w or w.lower() in nots or known(w) or known(w.lower()) or known(w.capitalize()):
                continue
            if not (w[0].isupper() or lowered):
                out.append(w)
    return list(dict.fromkeys(out))
