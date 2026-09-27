#!/usr/bin/env python3
"""The official documents the spine is imported from and checked against, as docs/spine/sources/official_documents.json
records them: where each is published and the fingerprint (sha256) of the copy the import read. `fetch()` downloads each
into data/spine_sources/ (gitignored) and refuses a copy whose fingerprint differs: the publisher has changed the file,
so the import is re-run and re-checked before the new copy is trusted. It also writes the NCF-SE text layer the import
reads. No model is called.
"""

import hashlib
import json
import urllib.request
from pathlib import Path

R = Path(__file__).resolve().parents[1]
DOCS = R / "docs/spine/sources/official_documents.json"
DATA = R / "data/spine_sources"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def fetch():
    """{"ncf": NCF-SE text, "elementary": PDF, "secondary": PDF}, each the official copy with the recorded fingerprint."""
    import pymupdf

    DATA.mkdir(parents=True, exist_ok=True)
    paths = {}
    for d in json.load(open(DOCS)):
        pdf = DATA / f"{d['key']}.pdf"
        if not pdf.exists() or sha256(pdf) != d["sha256"]:
            req = urllib.request.Request(
                d["url"], headers={"User-Agent": "Mozilla/5.0"}
            )
            pdf.write_bytes(urllib.request.urlopen(req, timeout=300).read())
        if (got := sha256(pdf)) != d["sha256"]:
            raise SystemExit(
                f"{d['url']} is not the copy the import read (sha256 {got}, recorded {d['sha256']}): "
                "re-import and re-check before trusting it"
            )
        paths[d["key"]] = str(pdf)
    text = DATA / "ncf.txt"
    text.write_text(
        "\n".join(p.get_text() for p in pymupdf.open(paths["ncf"])), encoding="utf-8"
    )
    return {**paths, "ncf": str(text)}


def fill(args):
    """Each source path not given on the command line becomes the fetched, fingerprint-checked official copy."""
    if not (args.ncf and args.elementary and args.secondary):
        for k, v in fetch().items():
            setattr(args, k, getattr(args, k) or v)
    return args
