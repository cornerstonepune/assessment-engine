"""Nothing in the curriculum spine is made up (goals/spine-traceable.yaml).

Nimish, 2026-09-27: "Tomorrow, anyone can trace back and say that we have not made something up." Every official line
imported into docs/spine/sources/ is looked up, in full and word for word, in the published document it cites, and that
document must be the very copy the import read: its address and fingerprint are in
docs/spine/sources/official_documents.json. research/spine_verify.py does the looking; these tests run it as anyone
would, from a directory that is not the repository, and show that it catches a changed word and a changed file and
asks again when the publisher drops a connection. The first run downloads NCERT's three PDFs (about 69 MB) into
data/spine_sources/; later runs reuse them.
"""

import hashlib
import importlib.util
import io
import json
import re
import subprocess
import sys
import time
import urllib.error
from pathlib import Path

import pymupdf
import pytest

from engine.core import db

RESEARCH = db.REPO_ROOT / "research"
ROWS = db.REPO_ROOT / "docs" / "spine" / "sources"
NCF, NCERT = "ncf_se_2023_competencies.json", "ncert_learning_outcomes.json"


def verify(cwd, *args):
    return subprocess.run(
        [sys.executable, str(RESEARCH / "spine_verify.py"), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=900,
    )


def test_every_official_line_in_the_spine_is_found_in_full_in_the_document_it_cites(tmp_path):
    ncf = json.loads((ROWS / NCF).read_text())
    lo = json.loads((ROWS / NCERT).read_text())
    run = verify(tmp_path)
    assert run.returncode == 0, run.stdout + run.stderr
    assert f"in the source: {len(ncf)}/{len(ncf)}" in run.stdout
    assert f"on their stated page: {len(lo)}/{len(lo)}" in run.stdout


def test_a_line_changed_by_one_word_is_caught(tmp_path):
    """The last word, not the first: a check that read only the start of each line would pass this."""
    changed = {}
    for name in (NCF, NCERT):
        rows = json.loads((ROWS / name).read_text())
        # the longest line: its last word sits far past the start a partial check would read
        row = max(rows, key=lambda r: len(r.get("text_full", r["text"])))
        field = "text_full" if "text_full" in row else "text"
        row[field] = row[field].rsplit(" ", 1)[0] + " invented"
        (tmp_path / name).write_text(json.dumps(rows, ensure_ascii=False))
        changed[name] = row["id"]
    run = verify(tmp_path, "--rows", str(tmp_path))
    assert run.returncode == 1, run.stdout + run.stderr
    for row_id in changed.values():
        assert f"not found: {row_id}" in run.stdout


def load_sources():
    spec = importlib.util.spec_from_file_location("spine_sources", RESEARCH / "spine_sources.py")
    sources = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sources)
    return sources


def test_a_publisher_file_that_is_not_the_copy_the_import_read_is_refused(tmp_path, monkeypatch):
    sources = load_sources()
    published = tmp_path / "published.pdf"
    published.write_bytes(b"%PDF-1.4 a later edition")
    (tmp_path / "official_documents.json").write_text(
        json.dumps([{"key": "ncf", "url": published.as_uri(), "sha256": "0" * 64}])
    )
    monkeypatch.setattr(sources, "DOCS", tmp_path / "official_documents.json")
    monkeypatch.setattr(sources, "DATA", tmp_path / "data")
    with pytest.raises(SystemExit, match="is not the copy the import read"):
        sources.fetch()


def publisher(tmp_path, monkeypatch, sources, replies):
    """A publisher at an https address whose answers, in turn, are `replies`: an error is raised, bytes are served."""
    doc = pymupdf.open()
    doc.new_page().insert_text((72, 72), "Curricular Goal 1")
    pdf = doc.tobytes()
    url = "https://ncert.nic.in/pdf/ncf.pdf"
    (tmp_path / "official_documents.json").write_text(
        json.dumps([{"key": "ncf", "url": url, "sha256": hashlib.sha256(pdf).hexdigest()}])
    )
    monkeypatch.setattr(sources, "DOCS", tmp_path / "official_documents.json")
    monkeypatch.setattr(sources, "DATA", tmp_path / "data")
    waits = []
    monkeypatch.setattr(time, "sleep", waits.append)

    def urlopen(req, timeout):
        assert req.full_url == url
        reply = replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return io.BytesIO(pdf)

    monkeypatch.setattr(sources.urllib.request, "urlopen", urlopen)
    return url, waits


def reset():
    return urllib.error.URLError(ConnectionResetError(104, "Connection reset by peer"))


def test_a_publisher_that_drops_the_connection_is_asked_again(tmp_path, monkeypatch):
    """ncert.nic.in reset CI's first TLS handshake on 2026-09-27 and served the same file seconds later."""
    sources = load_sources()
    _, waits = publisher(tmp_path, monkeypatch, sources, [reset(), reset(), "served"])
    got = sources.fetch()
    assert "Curricular Goal 1" in Path(got["ncf"]).read_text(encoding="utf-8")
    assert waits == [2, 4]


def test_a_publisher_that_never_answers_stops_the_run_naming_its_address(tmp_path, monkeypatch):
    sources = load_sources()
    url, waits = publisher(tmp_path, monkeypatch, sources, [reset() for _ in range(5)])
    with pytest.raises(SystemExit, match=f"{re.escape(url)} could not be downloaded in 5 attempts"):
        sources.fetch()
    assert waits == [2, 4, 8, 16]
