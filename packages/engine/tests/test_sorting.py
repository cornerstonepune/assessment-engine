"""`engine read file`: one scanned file of many papers sorts itself by the QR on each page.

Two papers are printed exactly as the engine prints them (`render_sheet`), then "scanned" — each page drawn to
pixels, tilted a little, and wrapped back into a PDF of photographs, as a school scanner hands them over — and
the two joined into one file, the second child's paper first page last.
"""

import json
import os
import random
import subprocess
import sys
import uuid

import cv2
import numpy as np
import pymupdf
import pytest

from engine.assess import items
from engine.assess.pick import Sheet
from engine.assess.render import render_sheet
from engine.core import db
from engine.w3_read import render_pdf, sorting


def test_pages_group_by_their_code_and_a_page_with_none_joins_the_paper_before_it():
    assert sorting.group(["CS00AAAA", "CS00AAAA", None, "CS00BBBB", None]) == [
        {"qr": "CS00AAAA", "pages": [1, 2, 3], "unread": [3]},
        {"qr": "CS00BBBB", "pages": [4, 5], "unread": [5]},
    ]
    assert sorting.group([None, "CS00AAAA"]) == [
        {"qr": None, "pages": [1], "unread": [1]},
        {"qr": "CS00AAAA", "pages": [2], "unread": []},
    ]


def test_copies_of_one_worksheet_in_a_row_are_cut_at_its_length_and_a_missing_code_starts_the_next_copy():
    three = {"R8-H02": 3}.get
    got = sorting.group(["R8-H02"] * 6 + [None, "R8-H02", "R8-H02"], lambda c: three(c, 0))
    assert [p["pages"] for p in got] == [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
    assert got[2] == {"qr": "R8-H02", "pages": [7, 8, 9], "unread": [7]}


def test_a_first_page_whose_code_did_not_read_belongs_to_the_copy_after_it_when_that_copy_is_short_by_it():
    """The Grade 2 scan of 2026-09-23: page 27 (R5-H14's first page) read no code, after a whole R2-E12 copy."""
    two = {"R2-E12": 2, "R5-H14": 2}.get
    got = sorting.group(["R2-E12", "R2-E12", None, "R5-H14", "R2-E12", "R2-E12"], lambda c: two(c, 0))
    assert [(p["qr"], p["pages"], p["unread"]) for p in got] == [
        ("R2-E12", [1, 2], []),
        ("R5-H14", [3, 4], [3]),
        ("R2-E12", [5, 6], []),
    ]
    # A whole copy after it takes nothing: the page stays the copy it was taken for, flagged.
    got = sorting.group(["R2-E12", "R2-E12", None, "R2-E12", "R2-E12", "R2-E12"], lambda c: two(c, 0))
    assert [p["pages"] for p in got] == [[1, 2], [3, 4], [5, 6]]


def _printed(tmp_path, qr, n):
    rng = random.Random(qr)
    qs = [items.bare_sum(rng, "R5", "Procedural", "+", 2, 2, [0]) for _ in range(n)]
    render_sheet(Sheet(qr, "G2", "Focus", 1, "W1", qs, title="Practice"), tmp_path, week_label="Practice")
    return tmp_path / f"{qr}.pdf"


def _scanned(pdfs, out):
    """Every page drawn at the reader's resolution, tilted a degree, and saved as a PDF of photographs."""
    doc = pymupdf.open()
    for path in pdfs:
        for img in render_pdf.render(path):
            h, w = img.shape[:2]
            tilt = cv2.getRotationMatrix2D((w / 2, h / 2), 1.0, 1.0)
            img = cv2.warpAffine(img, tilt, (w, h), borderValue=(255, 255, 255))
            img = np.clip(img.astype(int) + np.random.default_rng(1).integers(-12, 12, img.shape), 0, 255)
            ok, jpg = cv2.imencode(".jpg", img.astype(np.uint8), [cv2.IMWRITE_JPEG_QUALITY, 80])
            page = doc.new_page(width=595, height=842)
            page.insert_image(page.rect, stream=jpg.tobytes())
    doc.save(out)
    return out


@pytest.fixture
def scan(tmp_path):
    one, two = _printed(tmp_path, "CS00AAAA", 12), _printed(tmp_path, "CS00BBBB", 30)
    return _scanned([one, two], tmp_path / "class.pdf")


def test_every_page_of_a_scanned_file_is_read_by_its_qr(scan):
    codes = [sorting.qr_of(img) for img in render_pdf.render(scan)]
    assert codes[0] == "CS00AAAA" and set(codes) == {"CS00AAAA", "CS00BBBB"}, codes
    assert codes == sorted(codes), "each paper's pages together, in file order"


def _photographs(out, n, size=(2800, 2000)):
    """A file of `n` phone photographs as large as the 24 Sep ones (~2000 x 2800), each on its own PDF page."""
    doc = pymupdf.open()
    rng = np.random.default_rng(2)
    for _ in range(n):
        img = rng.integers(200, 255, (*size, 3), dtype=np.uint8)
        page = doc.new_page(width=595, height=842)
        page.insert_image(
            page.rect, stream=cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 60])[1].tobytes()
        )
    doc.save(out)
    return out


def _peak(path):
    """→ (the codes read, the most memory a process reading them held): measured in a process of its own, so
    what MuPDF keeps outside Python is counted too."""
    probe = (
        "import json, resource, sys; from engine.w3_read import sorting; c = sorting.codes(sys.argv[1]);"
        " print(json.dumps([c, resource.getrusage(resource.RUSAGE_SELF).ru_maxrss]))"
    )
    out = subprocess.run([sys.executable, "-c", probe, str(path)], capture_output=True, text=True, check=True)
    found, kb = json.loads(out.stdout.strip().splitlines()[-1])
    return found, kb * 1024


def test_a_files_codes_are_read_one_page_at_a_time(tmp_path):
    """On 2026-09-26 the engine was killed for memory four times reading the 24 Sep file: its 16 photographs
    were held at once to read their codes (750 MB), and MuPDF kept every decoded page besides (another 250 MB),
    on a server of 1.9 GB with no swap. Read a page at a time, each page more
    leaves less than a third of itself behind."""
    two, small = _peak(_photographs(tmp_path / "two.pdf", 2))
    ten, large = _peak(_photographs(tmp_path / "ten.pdf", 10))
    assert two == [None] * 2 and ten == [None] * 10
    page = 2800 * 2000 * 3  # one decoded photograph; held, each of eight more pages would add all of it
    assert large - small < 8 * page / 3, (
        f"{small / 2**20:.0f} MB for two pages, {large / 2**20:.0f} MB for ten"
    )


@pytest.fixture
def conn():
    if not os.getenv("DATABASE_URL"):
        pytest.skip("needs the local copy (bin/testdb)")
    with db.connect(db.dsn()) as c:
        yield c
        c.rollback()


def test_a_code_the_database_printed_names_its_child_and_paper_and_one_it_did_not_says_so(conn, scan):
    tenant = conn.execute(
        "insert into tenant (slug, name) values (%s, 't') returning id", (f"t-{uuid.uuid4()}",)
    )
    tenant = tenant.fetchone()["id"]
    child = conn.execute(
        "insert into child (tenant_id, roll_no, band, section) values (%s, '7', 'G2', 'G2') returning id",
        (tenant,),
    ).fetchone()["id"]
    template = conn.execute(
        "insert into sheet_template (tenant_id, band, level, week, key) values (%s, 'G2', 'L0', 'W1', %s)"
        " returning id",
        (tenant, '{"title": "Practice"}'),
    ).fetchone()["id"]
    conn.execute(
        "insert into sheet_instance (tenant_id, qr_code, sheet_template_id, child_id, kind)"
        " values (%s, 'CS00AAAA', %s, %s, 'focus')",
        (tenant, template, child),
    )
    first, second = sorting.sort_file(conn, scan)
    assert (
        first["qr"] == "CS00AAAA"
        and first["sheet"]["roll_no"] == "7"
        and first["sheet"]["paper"] == "Practice"
    )
    assert second["qr"] == "CS00BBBB" and second["ours"] and second["sheet"] is None


def test_a_class_of_library_worksheet_copies_sorts_into_one_paper_per_child(conn, tmp_path):
    """The Grade 2 scan of 2026-09-23: every copy of worksheet R8-H02 carries the code R8-H02. Two copies, and a
    copy of another worksheet between, come out as three papers, each named as the worksheet it is."""
    tenant = conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()
    if not tenant or not conn.execute("select 1 from skill_set where code = 'ADD.2D2D'").fetchone():
        pytest.skip("needs the seed loaded on the copy")
    for code in ("R8-H02", "R5-H14"):
        conn.execute(
            "insert into sheet_template (tenant_id, band, week, source, code, skill_set_code, difficulty)"
            " values (%s, 'G2', 'library', 'library', %s, 'ADD.2D2D', 'Hard')",
            (tenant["id"], code),
        )
    a1, b, a2 = (_printed(tmp_path / str(i), code, n) for i, (code, n) in enumerate(
        [("R8-H02", 30), ("R5-H14", 12), ("R8-H02", 30)]
    ))  # fmt: skip
    scan = _scanned([a1, b, a2], tmp_path / "class.pdf")
    length = len(pymupdf.open(a1))
    papers = sorting.sort_file(
        conn, scan, pages_of=lambda code: len(pymupdf.open(a1 if code == "R8-H02" else b))
    )
    assert [(p["qr"], len(p["pages"])) for p in papers] == [
        ("R8-H02", length),
        ("R5-H14", 1),
        ("R8-H02", length),
    ]
    assert all(p["worksheet"] and p["ours"] and not p["sheet"] for p in papers)
    assert papers[0]["worksheet"]["level"] == "Hard"


def test_a_code_printed_in_words_is_matched_to_the_code_printed_allowing_for_misread_letters():
    """2026-09-24: of sixteen one-page papers the QR scanned on three; the code printed beside it reads through."""
    mine = ["CS56DB32", "CSDEEED5", "CS3DB381"]
    assert sorting.printed_code(["Show your working · CS560832 · p1/1"], mine) == "CS56DB32"
    assert sorting.printed_code(["CSDEEEDS"], mine) == "CSDEEED5"
    assert sorting.printed_code(["C S 3DB381 p1/1"], mine) == "CS3DB381"
    assert sorting.printed_code(["no code here", "CS999999"], mine) is None
    assert sorting.printed_code(["CS56DB32", "CS3DB381"], mine) is None, "two papers on one page: nobody's"


def test_a_page_with_no_code_after_a_childs_whole_paper_is_nobodys_never_the_next_copy_of_it():
    one = {"CS00AAAA": 1, "R8-H02": 3}.get
    got = sorting.group(["CS00AAAA", None, "CS00BBBB"], lambda c: one(c, 0))
    assert [(p["qr"], p["pages"]) for p in got] == [("CS00AAAA", [1]), (None, [2]), ("CS00BBBB", [3])]
