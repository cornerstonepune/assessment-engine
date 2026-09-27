"""Nothing in the curriculum spine is made up (goals/spine-traceable.yaml).

Nimish, 2026-09-27: "Tomorrow, anyone can trace back and say that we have not made something up." Every official line
imported into docs/spine/sources/ is looked up, in full and word for word, in the published document it cites, and that
document must be the very copy the import read: its address and fingerprint are in
docs/spine/sources/official_documents.json. research/spine_verify.py does the looking; these tests run it as anyone
would, from a directory that is not the repository, and show that it catches a changed word and a changed file. The
first run downloads NCERT's three PDFs (about 69 MB) into data/spine_sources/; later runs reuse them.
"""

import importlib.util
import json
import subprocess
import sys

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


def test_a_publisher_file_that_is_not_the_copy_the_import_read_is_refused(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("spine_sources", RESEARCH / "spine_sources.py")
    sources = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sources)
    published = tmp_path / "published.pdf"
    published.write_bytes(b"%PDF-1.4 a later edition")
    (tmp_path / "official_documents.json").write_text(
        json.dumps([{"key": "ncf", "url": published.as_uri(), "sha256": "0" * 64}])
    )
    monkeypatch.setattr(sources, "DOCS", tmp_path / "official_documents.json")
    monkeypatch.setattr(sources, "DATA", tmp_path / "data")
    with pytest.raises(SystemExit, match="is not the copy the import read"):
        sources.fetch()
