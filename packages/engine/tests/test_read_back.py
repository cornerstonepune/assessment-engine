"""M5b: a paper the site prints for a child comes back (goals/md5b-read-back.yaml).

Every paper the paper maker prints — a class practice, a class assessment, a home assessment — is a child's own copy
with its own code (`focus_paper.print_paper`). A scan of a class's pile is read by those codes onto each child's copy, as
a library worksheet printed for a child is (`test_handout.py`); a copy that cannot be read is said, with why.

The handwriting reader is stood in, as in `test_the_loop.py`: what it reads is the answer written.
"""

from pathlib import Path

import pytest

from engine.w2_print import assemble, maker
from engine.w3_read import copies
from tests import test_maker, test_paper_from_library
from tests.test_copies import stand_in_reader
from tests.test_maker import _child
from tests.test_sorting import _scanned
from tests.test_the_loop import _counted, _planted, _round, _slots

conn = test_maker.conn  # the same fixture: the real schema, rolled back
children = test_paper_from_library.children  # three children of a class, named in `pii`

SECTION = "READBACK"
WEEK = "2026-W42-readback"
BY = "educator@school.test"
ASK = [{"skill_set": "MUL.2D1D", "level": "Medium", "n": 4}]


@pytest.fixture
def two(conn):
    conn.execute(
        "update skill set taught = true, taught_by = %s, taught_at = now() where code = %s",
        (BY, ASK[0]["skill_set"]),
    )
    return [_child(conn, "1", SECTION), _child(conn, "2", SECTION)]


def _items(conn, qr):
    return conn.execute(
        "select si.child_id, si.pdf_path, t.item_ids from sheet_instance si"
        " join sheet_template t on t.id = si.sheet_template_id where si.qr_code = %s",
        (qr,),
    ).fetchone()


@pytest.mark.parametrize("kind", sorted(maker.KINDS))
def test_every_kind_the_maker_prints_is_read_back_onto_each_childs_own_copy(
    conn, two, kind, tmp_path, monkeypatch, every_kind_trusted
):
    made = maker.make(conn, SECTION, two, WEEK, kind, "each", BY, ASK)
    for n, qr in enumerate(made["qrs"]):
        copy = _items(conn, qr)
        mistake, on = _planted(_slots(conn, copy["item_ids"]))
        assert on, f"{kind}: no question on {qr} can show a mistake"
        child = copy["child_id"]
        planted = _round(conn, child, qr, copy["pdf_path"], copy["item_ids"], mistake, tmp_path / f"{kind}-{n}.pdf",
                         monkeypatch, f"{kind}, {qr}")  # fmt: skip
        assert _counted(conn, child, mistake) == planted, f"{kind}: {qr}'s mistakes counted once signed off"


def test_a_home_assessment_made_again_in_the_week_leaves_the_earlier_one_readable_as_itself(
    conn, two, tmp_path, monkeypatch, every_kind_trusted
):
    """Nimish, 2026-10-21: an educator may make the week's home assessment again. A child who does the earlier paper
    anyway is read and marked on that paper, by its own code, against its own questions."""
    earlier = maker.make(conn, SECTION, two[:1], WEEK, "focus", "each", BY, ASK)["qrs"][0]
    newer = maker.make(conn, SECTION, two[:1], WEEK, "focus", "each", BY, ASK)["qrs"][0]
    assert newer != earlier
    copy = _items(conn, earlier)
    mistake, on = _planted(_slots(conn, copy["item_ids"]))
    assert on, f"no question on {earlier} can show a mistake"
    planted = _round(conn, copy["child_id"], earlier, copy["pdf_path"], copy["item_ids"], mistake,
                     tmp_path / "earlier.pdf", monkeypatch, f"earlier home assessment, {earlier}")  # fmt: skip
    assert _counted(conn, copy["child_id"], mistake) == planted, (
        "the earlier paper's mistakes counted once signed off"
    )
    read = conn.execute(
        "select si.qr_code from capture k join sheet_instance si on si.id = k.sheet_instance_id"
        " where si.child_id = %s and si.week = %s and k.superseded_by is null",
        (copy["child_id"], WEEK),
    ).fetchall()
    assert [r["qr_code"] for r in read] == [earlier], "read as the earlier paper, not the newer one"


def test_a_copy_whose_printed_page_is_not_kept_is_named_with_why_and_the_rest_of_the_pile_is_read(
    conn,
    two,
    tmp_path,
    monkeypatch,
    every_kind_trusted,
):
    made = maker.make(conn, SECTION, two, WEEK, "practice", "each", BY, ASK)
    pile = tmp_path / "pile.pdf"
    pile.write_bytes(maker.pdf(conn, made["qrs"]))
    gone = _items(conn, made["qrs"][1])
    kept = Path(gone["pdf_path"]).rename(tmp_path / "moved.pdf")
    try:
        monkeypatch.setattr(copies, "CUT", tmp_path / "scans")
        stand_in_reader(conn, _items(conn, made["qrs"][0])["item_ids"], monkeypatch)
        got = copies.read(conn, str(pile), "", [], BY)
    finally:
        kept.rename(gone["pdf_path"])
    whose = {c["child_id"]: c for c in got}
    assert len(got) == 2, f"each copy in the pile has its line: {got}"
    read = whose[_items(conn, made["qrs"][0])["child_id"]]
    assert read["by_code"] and not read.get("skipped") and read["answers"], read
    unread = whose[gone["child_id"]]
    assert unread.get("skipped") and "printed" in unread["why"], unread


def test_a_spare_copy_is_read_onto_the_child_whose_name_is_said_for_it_and_without_one_is_named_not_dropped(
    conn, children, tmp_path, monkeypatch, every_kind_trusted
):
    """The classroom contract (the workflow's N8): a child who finishes early takes the next spare and writes their name
    on it; a spare is matched by that name. A spare carries a code but no child, so it was neither a copy printed for a
    child nor a bare worksheet, and was in no line of what the reading returned."""
    built = test_paper_from_library._week(conn, WEEK)
    assemble.render(conn, built, tmp_path / "pack", WEEK, BY)
    spare = built["spares"][0]
    pdf = conn.execute(
        "select pdf_path from sheet_instance where id = %s", (spare["instance_id"],)
    ).fetchone()
    stand_in_reader(conn, [r["id"] for r in spare["item_rows"]], monkeypatch)
    monkeypatch.setattr(copies, "CUT", tmp_path / "scans")

    (unsaid,) = copies.read(conn, _scanned([pdf["pdf_path"]], tmp_path / "inbox.pdf"), "", None, BY)
    assert unsaid.get("skipped") and "whose" in unsaid["why"], unsaid

    scan = _scanned([pdf["pdf_path"]], tmp_path / "spare.pdf")
    (got,) = copies.read(conn, scan, test_paper_from_library.SECTION, ["Riya"], BY)
    assert got["child_id"] == children[1] and not got.get("skipped") and got["answers"], got
    landed = conn.execute(
        "select si.qr_code, si.child_id from capture c join sheet_instance si on si.id = c.sheet_instance_id"
        " where c.id = %s",
        (got["capture_id"],),
    ).fetchone()
    assert (landed["qr_code"], landed["child_id"]) == (spare["qr"], children[1]), (
        "the spare is now Riya's copy"
    )
