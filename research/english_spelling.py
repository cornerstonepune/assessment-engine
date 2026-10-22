#!/usr/bin/env python3
"""Every word an English sample puts on a paper or in its key is a British English word (supabase/seed/english/).

Read against the en_GB Hunspell dictionary that LibreOffice ships, fetched at a pinned commit into data/dictionaries/
and refused if its fingerprint differs. Checked: the passages, each sample's instruction, its text, its right answer (sort groups and table boxes too),
the answers also accepted, the key points a marker looks for, and every printed option except those listed as a
likely wrong answer. Not checked: the likely wrong answers, which are misspelt on purpose, and the text of a
"find and fix the mistakes" question. A sample may show a child a word that is not one on purpose (a misspelling
to correct, a word part such as -ing or ough): it lists it in `not_words`, and the check holds that the dictionary
really does not know it. A word with a capital letter that the dictionary does not know is a name
(Meera, Kothrud) and is listed, not failed. Indian English words a Pune classroom uses are in
research/english_words.txt, one per line with what it means, so each is a decision someone can read.

uv run --no-project --with spylls==0.1.7 python research/english_spelling.py              # exit 1 on any fault
uv run --no-project --with spylls==0.1.7 python research/english_spelling.py --chunk DIR  # a draft in DIR
"""

import argparse
import hashlib
import re
import sys
import urllib.request
from pathlib import Path

R = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R / "research"))
import english_check as ec  # noqa: E402

COMMIT = "67032ee957631908098a72edf48dc81cac27e369"
SHA256 = {
    "dic": "04e90f34f5263bf26780e9c4a442e9ad16584e227af49ddd1b3b21b01df5b29c",
    "aff": "0fd6ed120ef28957847d98ba5149b117e27116cf81b5aa36208453f6755a36fd",
}
HERE = R / "data/dictionaries"
def dictionary():
    from spylls.hunspell import Dictionary

    HERE.mkdir(parents=True, exist_ok=True)
    for ext, want in SHA256.items():
        path = HERE / f"en_GB.{ext}"
        if not path.exists():
            url = f"https://raw.githubusercontent.com/LibreOffice/dictionaries/{COMMIT}/en/en_GB.{ext}"
            path.write_bytes(urllib.request.urlopen(url, timeout=60).read())
        if hashlib.sha256(path.read_bytes()).hexdigest() != want:
            raise SystemExit(f"{path}: fingerprint differs from the pinned en_GB dictionary")
    return Dictionary.from_files(str(HERE / "en_GB"))


def allowed(chunk=None):
    paths = [R / "research/english_words.txt"] + ([Path(chunk) / "english_words.txt"] if chunk else [])
    lines = [ln for p in paths if p.exists() for ln in p.read_text().splitlines()]
    return {ln.split("—")[0].strip().lower() for ln in lines if ln.strip() and not ln.startswith("#")}


def texts(t):
    """(where, text, words shown on purpose that are not words, whether capitals were taken away on purpose)."""
    for p in t["passage"]:
        yield f"passage {p['code']}", p["text"], set(), False
        yield f"passage {p['code']} title", p.get("title") or "", set(), False
    for s in t["skill_level_sample"]:
        label = f"{s['skill_code']} {s['difficulty']} {s['question_type']} #{s['n']}"
        wrong, nots = set(s.get("wrong") or {}), {w.lower() for w in s.get("not_words") or []}
        yield label, s.get("ask") or "", nots, False
        if s["question_type"] != "ENG.CORRECT":
            yield label, s.get("text") or "", nots, s["question_type"] == "ENG.PUNCTUATE"
        for v in (s.get("answer"), s.get("accept")):
            for x in ec.flat(v):
                yield label, x, nots, False
        for x in s.get("key_points") or []:
            yield label, x, set(), False
        for x in ec.flat(s.get("options")):
            if x not in wrong:
                yield label, x, nots, False


WORD = re.compile(r"[A-Za-z]+(?:['’-][A-Za-z]+)*")


def check(t, known, extra):
    faults, names, words, shown = [], set(), 0, 0
    for where, text, nots, lowered in texts(t):
        for raw in WORD.findall(text.replace("’", "'")):
            if known(raw) or raw.lower() in extra:
                words += 1
                continue
            for w in raw.split("-"):
                w = re.sub(r"'s$|s'$", "", w) if len(w) > 3 else w
                if not w:
                    continue
                words += 1
                if w.lower() in nots:
                    shown += 1
                    if known(w) or known(w.lower()):
                        faults.append(f"{where}: {w!r} is listed as not a word, but the dictionary knows it")
                    continue
                if w.lower() in extra or known(w) or known(w.lower()) or known(w.capitalize()):
                    continue
                if w[0].isupper() or lowered:
                    names.add(w.capitalize())
                else:
                    faults.append(f"{where}: {w!r} is not a British English word")
    return faults, sorted(names), words, shown


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--chunk")
    ap.add_argument("--only", default="")
    a = ap.parse_args(argv)
    d = dictionary()
    cache = {}

    def known(w):
        if w not in cache:
            cache[w] = d.lookup(w)
        return cache[w]

    faults, names, words, shown = check(ec.load(chunk=a.chunk), known, allowed(a.chunk))
    if only := tuple(p for p in a.only.split(",") if p):
        faults = [f for f in faults if any(p in f for p in only)]
    print(f"{words} words read against en_GB ({COMMIT[:7]}); {len(set(cache))} different")
    print(f"{shown} words shown on purpose that are not words (a misspelling to fix, a word part), each unknown to it")
    print(f"names, not failed ({len(names)}): {', '.join(names)}")
    for f in faults:
        print("FAULT", f)
    print(f"{len(faults)} faults")
    return 1 if faults else 0


if __name__ == "__main__":
    sys.exit(main())
