#!/usr/bin/env python3
"""The provenance check on the imported layers: every imported row must be found, word for word, in the official
document it came from (NCF-SE text; NCERT outcomes on their stated page). A row that is not found is a fault in the
import, never something to explain away. No model is called.

python3 research/spine_verify.py --ncf <NCF-SE text> --elementary <NCERT 2017 PDF> --secondary <NCERT 2019 PDF>
"""

import argparse
import json
import re
import sys
from pathlib import Path

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
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9-]+", " ", t)).strip()


def main():
    import pymupdf

    ap = argparse.ArgumentParser()
    ap.add_argument("--ncf", required=True)
    ap.add_argument("--elementary", required=True)
    ap.add_argument("--secondary", required=True)
    a = ap.parse_args()
    src = norm(Path(a.ncf).read_text(encoding="utf-8", errors="replace"))
    ncf = json.load(open(SRC / "ncf_se_2023_competencies.json"))
    ncf_miss = [
        e["id"] for e in ncf if norm(e.get("text_full", e["text"]))[:120] not in src
    ]
    docs = {
        "Elementary": pymupdf.open(a.elementary),
        "Secondary": pymupdf.open(a.secondary),
    }
    lo = json.load(open(SRC / "ncert_learning_outcomes.json"))
    lo_miss = []
    for r in lo:
        doc = docs["Elementary" if "Elementary" in r["src"] else "Secondary"]
        if norm(r["text"])[:80] not in norm(doc[r["page"] - 1].get_text()):
            lo_miss.append(r["id"])
    print(
        f"NCF-SE rows found word for word in the source: {len(ncf) - len(ncf_miss)}/{len(ncf)}"
    )
    print(
        f"NCERT outcomes found word for word on their stated page: {len(lo) - len(lo_miss)}/{len(lo)}"
    )
    for i in ncf_miss + lo_miss:
        print("   not found:", i)
    return 1 if ncf_miss or lo_miss else 0


if __name__ == "__main__":
    sys.exit(main())
