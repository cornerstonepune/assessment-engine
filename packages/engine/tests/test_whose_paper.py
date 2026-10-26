"""Whose paper is it (`w3_read/whose_paper.py`, goals/chk_whose_paper.yaml): beside an answer's photograph, the copy and
page it is and the code printed on it; and a notice, worked out by code, where the same picture sits on two children's
copies of one scan file or a page carries another child's code — Yes is not allowed on it until a person chooses.
Nimish, 2026-10-23: "I think we should have a very clear mechanism for marking this per child.\""""

import io

import pymupdf
import pytest
import segno

from engine.core import db
from engine.w3_read import whose_paper as W


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


def _png(text, size=300):
    buf = io.BytesIO()
    segno.make(text, error="h").save(buf, kind="png", scale=max(4, size // 33), border=4)
    return buf.getvalue()


def _pdf(path, pages):
    """A scan: one photograph per page, each a QR of the text given for it."""
    doc = pymupdf.open()
    for text in pages:
        page = doc.new_page()
        page.insert_image(page.rect, stream=_png(text))
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(path)
    return path


def _copy(conn, folder, k, code, pages, texts, section="TESTWHOSE"):
    """A child, their paper printed with `code`, and the copy `k` of the scan cut from `texts`."""
    tenant = conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]
    child = conn.execute(
        "insert into child (tenant_id, roll_no, section, band) values (%s,%s,%s,'G1') returning id",
        (tenant, str(k), section),
    ).fetchone()["id"]
    template = conn.execute(
        "insert into sheet_template (tenant_id, band, week) values (%s,'G1','test') returning id", (tenant,)
    ).fetchone()["id"]
    sheet = conn.execute(
        "insert into sheet_instance (tenant_id, sheet_template_id, child_id, qr_code) values (%s,%s,%s,%s) returning id",
        (tenant, template, child, code),
    ).fetchone()["id"]
    path = _pdf(folder / f"copy{k:02d}-p1-{code}.pdf", texts)
    return conn.execute(
        "insert into capture (tenant_id, path, pages, sheet_instance_id, qr_read) values (%s,%s,%s,%s,%s) returning id",
        (tenant, str(path), pages, sheet, code),
    ).fetchone()["id"]


def test_a_page_says_which_copy_of_the_file_and_which_page_of_the_copy_it_is(conn, tmp_path):
    folder = tmp_path / "scan-a"
    a = _copy(conn, folder, 1, "CS1A2B3C", 2, ["CS1A2B3C", "page two of one"])
    _copy(conn, folder, 6, "CS4D5E6F", 1, ["CS4D5E6F"])
    p = W.proof(conn, a, 2)
    assert (p["scan"], p["copy"], p["copies"], p["page"], p["pages"]) == ("scan-a", 1, 6, 2, 2)
    assert p["printed_with"] == "CS1A2B3C" and p["problem"] is None and W.may_confirm(p)


def test_the_code_is_read_off_the_page_itself(conn, tmp_path):
    a = _copy(conn, tmp_path / "scan-b", 3, "CS000003", 1, ["CS000003"])
    assert W.proof(conn, a, 1)["code"] == "CS000003"


def test_the_same_picture_on_two_childrens_copies_is_a_notice_and_yes_waits_for_a_person(conn, tmp_path):
    folder = tmp_path / "scan-c"
    a = _copy(conn, folder, 1, "CS00000A", 1, ["CS00000A"])
    b = _copy(conn, folder, 2, "CS00000B", 1, ["CS00000A"])  # copy 2 holds copy 1's photograph
    p = W.proof(conn, b, 1)
    assert p["problem"]["kind"] == W.SAME and "copy 1" in p["problem"]["text"]
    assert not W.may_confirm(p)
    assert W.proof(conn, a, 1)["problem"]["kind"] == W.SAME  # and copy 1 says so of copy 2
    assert W.may_confirm(W.choose(conn, b, 1, "theirs", "Aseem"))
    assert not W.may_confirm(
        W.choose(conn, b, 1, "not_theirs", "Aseem")
    )  # a changed mind is a new row, the latest stands
    assert conn.execute("select count(*) n from page_choice where capture_id = %s", (b,)).fetchone()["n"] == 2


def test_a_page_with_another_childs_code_is_a_notice(conn, tmp_path):
    a = _copy(conn, tmp_path / "scan-d", 1, "CS00000A", 1, ["CS00000F"])
    p = W.proof(conn, a, 1)
    assert p["problem"]["kind"] == W.WRONG and "CS00000F" in p["problem"]["text"]


def test_two_photographs_of_different_pages_are_no_notice(conn, tmp_path):
    folder = tmp_path / "scan-e"
    _copy(conn, folder, 1, "CS00000A", 1, ["CS00000A"])
    b = _copy(conn, folder, 2, "CS00000B", 1, ["CS00000B"])
    assert W.proof(conn, b, 1)["problem"] is None


def test_a_choice_needs_a_notice_and_a_known_word(conn, tmp_path):
    a = _copy(conn, tmp_path / "scan-f", 1, "CS00000A", 1, ["CS00000A"])
    with pytest.raises(ValueError, match="no notice"):
        W.choose(conn, a, 1, "theirs", "Aseem")
    with pytest.raises(ValueError, match="theirs"):
        W.choose(conn, a, 1, "maybe", "Aseem")


def test_a_worksheets_own_code_is_not_a_wrong_child():
    assert W.verdict("R8-H02", "CS00000A", []) is None
    assert W.verdict(None, "CS00000A", []) is None
    assert W.verdict("CS00000A", "CS00000A", []) is None


def test_a_page_is_told_once_and_the_card_never_draws_a_photograph_again(conn, tmp_path, monkeypatch):
    """Nimish, 2026-10-26: "Once I click what the child has written, it literally takes a few seconds to go to the next
    one." Every card drew the photograph of every page of every copy in its file to tell whose paper it is: about half a
    second a page. A page's picture and printed code are facts of a file that never changes, told once (`record`) and
    kept as rows; a card reads the rows."""
    folder = tmp_path / "scan-g"
    a = _copy(conn, folder, 1, "CS00000A", 2, ["CS00000A", "page two"])
    b = _copy(
        conn, folder, 2, "CS00000B", 2, ["CS00000A", "page two of b"]
    )  # copy 2's page 1 is copy 1's photograph
    W.record(conn, a)
    W.record(conn, b)
    told = conn.execute(
        "select count(*) n from capture_page where capture_id in (%s, %s)", (a, b)
    ).fetchone()["n"]
    assert told == 4

    def drawn(*_args, **_kw):
        raise AssertionError("a card drew a photograph its rows already tell")

    monkeypatch.setattr(W.render_pdf, "photo", drawn)
    p = W.proof(conn, b, 1)
    assert p["problem"]["kind"] == W.SAME and p["code"] == "CS00000A"
    assert W.proof(conn, a, 2)["problem"] is None


def test_a_page_read_before_its_rows_existed_is_told_on_its_first_card_and_kept(conn, tmp_path, monkeypatch):
    a = _copy(conn, tmp_path / "scan-h", 1, "CS00000A", 1, ["CS00000A"])
    assert W.proof(conn, a, 1)["code"] == "CS00000A"  # no row yet: told now, and kept
    monkeypatch.setattr(
        W.render_pdf, "photo", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("drawn twice"))
    )
    assert W.proof(conn, a, 1)["code"] == "CS00000A"
