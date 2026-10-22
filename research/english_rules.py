"""The English rules code can compute, so a drafted example is checked rather than trusted (CLAUDE.md: "a model may
draft, code verifies"). Each function works out an answer, or tests one, from the example's own inputs: the spelling
of a verb with -ing, a plural, an apostrophe of possession, a word with a prefix or suffix, alphabetical order, the
order of events in a passage, a page in an index. Used by research/english_check.py; no file, no network.
"""

import difflib
import re

VOWELS = "aeiou"
WORD = re.compile(r"[A-Za-z0-9]+(?:['’][A-Za-z]+)*")


def words(text):
    """The words of a text, an apostrophe kept inside a word (don't, girls')."""
    return WORD.findall(text or "")


def plain(text):
    """Lower case, curly apostrophes and quotes straightened, spaces single: for comparing what a child wrote."""
    text = (text or "").replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    return " ".join(text.lower().split())


def letters(text):
    return re.sub(r"[^a-z0-9]", "", plain(text))


def _consonant(c):
    return c.isalpha() and c not in VOWELS


def syllables(word):
    """Vowel groups, a final silent e not counted: a rough count, enough to tell one syllable from more."""
    w = word.lower()
    groups = re.findall(r"[aeiouy]+", w)
    n = len(groups)
    if w.endswith("e") and not w.endswith(("le", "ee", "ye")) and n > 1:
        n -= 1
    return max(n, 1)


def doubles(base, stress_last=False):
    """A short vowel between two consonants at the end doubles its consonant (hop, hopping), in one syllable or
    where the last syllable is stressed (begin, beginning). Never w, x or y."""
    b = base.lower()
    return (
        len(b) >= 3
        and _consonant(b[-1])
        and b[-1] not in "wxy"
        and b[-2] in VOWELS
        and _consonant(b[-3])
        and (syllables(b) == 1 or stress_last)
    )


def add_ending(base, ending, stress_last=False):
    """A verb with -s, -ed or -ing, by the rules Stage 3 teaches (3Ww.02)."""
    b = base.lower()
    if ending == "s":
        if b.endswith(("s", "x", "z", "ch", "sh")) or (b.endswith("o") and _consonant(b[-2])):
            return b + "es"
        if b.endswith("y") and _consonant(b[-2]):
            return b[:-1] + "ies"
        return b + "s"
    if ending == "ed":
        if b.endswith("e"):
            return b + "d"
        if b.endswith("y") and _consonant(b[-2]):
            return b[:-1] + "ied"
        return b + b[-1] + "ed" if doubles(b, stress_last) else b + "ed"
    if ending == "ing":
        if b.endswith("ie"):
            return b[:-2] + "ying"
        if b.endswith("e") and not b.endswith(("ee", "ye", "oe")):
            return b[:-1] + "ing"
        return b + b[-1] + "ing" if doubles(b, stress_last) else b + "ing"
    raise ValueError(f"no rule for the ending {ending!r}")


def plural(base, f_to_ves=False, o_es=False):
    """A noun's plural by the patterns Stage 4 teaches (4Ww.02): -s, -es, -y/-ies, -f/-ves."""
    b = base.lower()
    if f_to_ves:
        return b[:-2] + "ves" if b.endswith("fe") else b[:-1] + "ves"
    if b.endswith(("s", "x", "z", "ch", "sh")) or (o_es and b.endswith("o")):
        return b + "es"
    if b.endswith("y") and _consonant(b[-2]):
        return b[:-1] + "ies"
    return b + "s"


def possessive(owner, many=False):
    """The apostrophe of possession (4Wg.03): one owner 's; many owners ending in s, an apostrophe alone; many owners
    not ending in s (children), 's."""
    return owner + "'" if many and owner.endswith("s") else owner + "'s"


def affix(root, prefix=None, suffix=None):
    """A root with a prefix (no change) or a suffix: y after a consonant turns to i, and a final e drops before a
    suffix that starts with a vowel (3Ww.03, 4Ww.03)."""
    r = root.lower()
    if prefix:
        return prefix.lower().strip("-") + r
    s = suffix.lower().strip("-")
    if r.endswith("y") and _consonant(r[-2]):
        r = r[:-1] + "i"
    elif r.endswith("e") and s[0] in VOWELS:
        r = r[:-1]
    return r + s


def contraction_fits(short, full):
    """A short form keeps only letters of the two words, in order, with an apostrophe where letters went."""
    s, f = letters(short), letters(full)
    it = iter(f)
    return "'" in plain(short) and all(c in it for c in s) and len(s) < len(f)


def depth(a, b):
    """The letter that decides which of two words comes first in a dictionary: 1 for the first letter."""
    a, b = a.lower(), b.lower()
    for i, (x, y) in enumerate(zip(a, b, strict=False), 1):
        if x != y:
            return i
    return min(len(a), len(b)) + 1


def alphabetical(items):
    """(the items in dictionary order, the deepest letter any neighbouring pair needs)."""
    ordered = sorted(items, key=str.lower)
    return ordered, max((depth(a, b) for a, b in zip(ordered, ordered[1:], strict=False)), default=0)


def found(part, text):
    """A phrase in a text, case, curly quotes, spacing and end punctuation ignored."""
    return plain(part).strip(" .,!?;:\"'") in plain(text)


def passage_order(items, passage):
    """The items in the order the passage tells them, or None if one is not in it word for word."""
    p = plain(passage)
    at = {i: p.find(plain(i).strip(" .,!?;:\"'")) for i in items}
    return None if min(at.values(), default=0) < 0 else sorted(items, key=at.get)


INDEX_LINE = re.compile(r"^\s*(.+?)\s*(?:\.{2,}|…+|:|\s[–-]\s)\s*(\d+(?:\s*[–-]\s*\d+)?(?:,\s*\d+)*)\s*$")


def index_pages(passage):
    """A contents page or an index as {entry: pages}, one entry per line: 'Frogs ..... 12' or 'Frogs: 12, 15'."""
    out = {}
    for line in passage.splitlines():
        if m := INDEX_LINE.match(line):
            out[plain(m.group(1))] = m.group(2).replace(" ", "")
    return out


def alliterates(phrase, at_least=2):
    """At least `at_least` neighbouring words share a first letter (articles and small words between them allowed)."""
    small = {"a", "an", "the", "and", "of", "in", "on", "to", "with", "at", "by", "is", "was"}
    heads = [w[0].lower() for w in words(phrase) if w.lower() not in small]
    run = best = 1 if heads else 0
    for x, y in zip(heads, heads[1:], strict=False):
        run = run + 1 if x == y else 1
        best = max(best, run)
    return best >= at_least


def simile(phrase):
    return bool(re.search(r"\blike\b|\bas \w+ as\b", plain(phrase)))


def same_words(a, b):
    """The same words in the same order, punctuation and case ignored: what punctuating a sentence must keep."""
    return [w.lower() for w in words(a)] == [w.lower() for w in words(b)]


def corrections(text, answer):
    """How many words a correction changed, added or took out."""
    a, b = [w.lower() for w in words(text)], [w.lower() for w in words(answer)]
    ops = difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes()
    return sum(max(i2 - i1, j2 - j1) for tag, i1, i2, j1, j2 in ops if tag != "equal")


def narration(passage):
    """'first' when the narrator says I, we or my outside speech marks; else 'third'."""
    outside = re.sub(r"[\"“][^\"”]*[\"”]", " ", passage or "")
    return "first" if re.search(r"\b(I|we|We|my|My|our|Our|me)\b", outside) else "third"
