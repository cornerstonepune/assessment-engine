#!/usr/bin/env python3
"""The provenance check on the imported layers: every imported row must be found in full, word for word and in order,
in the official document it came from (NCF-SE text; NCERT outcomes on their stated page). Case, punctuation and line
breaks are ignored; words are not. A row that is not found is a fault in the import, never something to explain away.
No model is called.

python3 research/spine_verify.py      # fetches the official copies (research/spine_sources.py) and checks against them
python3 research/spine_verify.py --ncf <NCF-SE text> --elementary <NCERT 2017 PDF> --secondary <NCERT 2019 PDF>
"""

import argparse
import json
import re
import sys
from pathlib import Path

from spine_sources import fill

SRC = Path(__file__).resolve().parents[1] / "docs/spine/sources"


def norm(t):
    t = (
        t.lower()
        .replace("­", "")
        .replace("’", "'")
        .replace("‘", "'")
        .replace("“", '"')
        .replace("”", '"')
    )
    t = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1-\2", t)
    t = re.sub(r"[^a-z0-9-]+", " ", t)
    # a hyphen joins two words; standing alone it is punctuation
    t = re.sub(r"(?<![a-z0-9])-+|-+(?![a-z0-9])", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def main():
    import pymupdf

    ap = argparse.ArgumentParser()
    ap.add_argument("--ncf")
    ap.add_argument("--elementary")
    ap.add_argument("--secondary")
    ap.add_argument("--rows", default=str(SRC), help="the imported rows to check")
    a = fill(ap.parse_args())
    src = norm(Path(a.ncf).read_text(encoding="utf-8", errors="replace"))
    ncf = json.load(open(Path(a.rows) / "ncf_se_2023_competencies.json"))
    ncf_miss = [e["id"] for e in ncf if norm(e.get("text_full", e["text"])) not in src]
    docs = {
        "Elementary": pymupdf.open(a.elementary),
        "Secondary": pymupdf.open(a.secondary),
    }
    lo = json.load(open(Path(a.rows) / "ncert_learning_outcomes.json"))
    lo_miss = []
    for r in lo:
        doc = docs["Elementary" if "Elementary" in r["src"] else "Secondary"]
        if norm(r["text"]) not in norm(doc[r["page"] - 1].get_text()):
            lo_miss.append(r["id"])
    print(
        f"NCF-SE rows found in full, word for word, in the source: {len(ncf) - len(ncf_miss)}/{len(ncf)}"
    )
    print(
        f"NCERT outcomes found in full, word for word, on their stated page: {len(lo) - len(lo_miss)}/{len(lo)}"
    )
    for i in ncf_miss + lo_miss:
        print("   not found:", i)
    return 1 if ncf_miss or lo_miss else 0


if __name__ == "__main__":
    sys.exit(main())
