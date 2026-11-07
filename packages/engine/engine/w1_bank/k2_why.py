"""Why a draft's steps name a thing the materials do not, in counts (goals/m1-12o-draft-why.yaml).

The step rule holds a page back when a step names a prop of the band that the page's own materials text does not. It
does not look at what else the school wrote on the page, so a hit may be a thing the school's page does name, or a
spelling of a thing it lists, or a prop nearly every page lists, or a word used in another sense. Before the rule is
changed, this puts each hit of the latest draft of each page in the first class that fits it. Pure: no database, no
model. It holds no phrase of the school's: counts, and plain single words that repeat (the log is public).
"""

from collections import Counter
from collections.abc import Iterable, Mapping

from engine.w1_bank import k2_batch as batch
from engine.w1_bank import k2_format as fmt

CLASSES = ("named_on_the_page", "variant_of_a_listed_word", "listed_on_most_pages", "not_named_anywhere")
SCHOOL_TEXT = ("name", "objective", "steps", "thinking", "level_0", "level_1", "level_2", "level_3")
SHOWN = 25  # the most distinct words one class prints


def _stems(text: str) -> set[str]:
    return {t for t in batch._tokens(text) if t.isalpha()}


def _printable(word: str) -> bool:
    """A word the log may show: letters only, at most 12 of them, so never a phrase of the school's own text."""
    return word.isascii() and word.isalpha() and len(word) <= 12


def latest_steps(kept: Iterable[tuple[str, object]], pages: set[str]) -> dict[str, list[str]]:
    """For each page, the steps of the last kept reply that has them (a refused reply is nothing)."""
    out: dict[str, list[str]] = {}
    for outcome, reply in kept:
        if outcome == "refused":
            continue
        for it in batch.items(reply, "pages"):
            steps = it.get("steps") if isinstance(it, dict) else None
            if isinstance(it, dict) and it.get("key") in pages and isinstance(steps, list):
                if all(isinstance(x, str) for x in steps):
                    out[it["key"]] = steps
    return out


def _class_of(stem: str, row: dict, listed: set[str], shared: Mapping[str, float]) -> str:
    if stem in _stems(" ".join(str(row.get(c) or "") for c in SCHOOL_TEXT)):
        return CLASSES[0]
    near = any(
        len(m) >= 4 and len(stem) >= 4 and (m[:4] == stem[:4] or m in stem or stem in m) for m in listed
    )
    if near:
        return CLASSES[1]
    return CLASSES[2] if shared.get(stem, 0.0) > 0.5 else CLASSES[3]


def why(
    steps: Mapping[str, list[str]], rows: Mapping[str, dict], vocab: frozenset[str], format_row: dict
) -> dict:
    """The hits of `steps` (each page's latest draft) put in a class, with the pages each class would clear."""
    with_list = [r for r in rows.values() if (r.get("materials") or "").strip()]
    shared = Counter(w for r in with_list for w in _stems(r["materials"]))
    share = {w: n / len(with_list) for w, n in shared.items()} if with_list else {}
    hits: Counter[str] = Counter()
    seen: dict[str, Counter[str]] = {c: Counter() for c in CLASSES}
    classes_per_page: list[set[str]] = []
    for key, lines in steps.items():
        row = rows.get(key) or {}
        found = fmt.unlisted_step_words(lines, row.get("materials") or "", vocab, format_row)
        if not found:
            continue
        listed = _stems(row.get("materials") or "")
        per = set()
        for _, word in dict.fromkeys(found):
            c = _class_of(batch._stem(word), row, listed, share)
            hits[c] += 1
            seen[c][batch._stem(word)] += 1
            per.add(c)
        classes_per_page.append(per)
    clear = {}
    for i, name in enumerate(
        ("named_on_the_page", "plus_variant_of_a_listed_word", "plus_listed_on_most_pages")
    ):
        allowed = set(CLASSES[: i + 1])
        clear[name] = sum(1 for per in classes_per_page if per <= allowed)
    words = {
        c: dict(Counter({w: n for w, n in got.items() if n >= 2 and _printable(w)}).most_common(SHOWN))
        for c, got in seen.items()
    }
    words = {c: w for c, w in words.items() if w}
    shown = sum(sum(w.values()) for w in words.values())
    return {
        "pages": len(classes_per_page),
        "hits": {c: hits[c] for c in CLASSES},
        "pages_clear_if": clear,
        "words": words,
        "once": sum(hits.values()) - shown,
    }
