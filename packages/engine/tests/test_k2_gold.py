"""A sheet for people to mark drafts keep or reject, so the machine's verdicts can be scored against theirs
(goals/m1-11f-draft-rules.yaml). The machine's own verdict, confidence and reason are never on it: a person who has read
them marks differently."""

import csv
import io
import os

import pytest

from engine.w1_bank import k2_gold as gold
from engine.w1_bank import map_ledger
from engine.w1_bank.k2_gaps import PAGE_PARTS
from tests import test_k2_draft as base

conn = base.conn
FULL, Scripted, _act, drafted, run, AGREE = (
    base.FULL,
    base.Scripted,
    base._act,
    base.drafted,
    base.run,
    base.AGREE,
)

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")


@pytest.fixture
def pages(conn):
    for code, strand in (
        ("KX-1", "Block Room"),
        ("KX-2", "Block Room"),
        ("KX-3", "Sensorial"),
        ("KX-4", "Sensorial"),
    ):
        _act(
            conn,
            code,
            f"Activity {code}",
            strand=strand,
            materials=f"materials of {code}",
            objective="the school's own",
        )
    run(
        conn,
        Scripted(
            {("k2_page_draft", c): [drafted(objective="x")] for c in ("KX-1", "KX-2", "KX-3", "KX-4")}
            | {("k2_page_check", c): [AGREE] for c in ("KX-1", "KX-2", "KX-3", "KX-4")}
        ),
    )
    map_ledger.apply(conn, conn.t, conn.staff, True)
    return conn


def test_the_sheet_takes_pages_from_every_section_and_the_same_ones_every_time(pages):
    a = gold.sheet(pages, pages.t, base.BAND, 2)
    b = gold.sheet(pages, pages.t, base.BAND, 2)
    assert [r["code"] for r in a] == [r["code"] for r in b]
    assert len({r["section"] for r in a}) == 2, "one from each section before a second from either"


def test_each_row_has_the_school_text_beside_the_draft_and_says_which_is_which(pages):
    (row,) = gold.sheet(pages, pages.t, base.BAND, 1)
    assert row["materials"].startswith("materials of KX-")
    assert row["objective"] == "the school's own" and row["objective_by"] == "school"
    assert row["steps_by"] == "drafted" and row["steps"]
    assert row["verdict"] == "" and row["what_is_wrong"] == ""


def test_nothing_the_machine_said_of_a_draft_is_on_the_sheet(pages):
    rows = gold.sheet(pages, pages.t, base.BAND, 4)
    assert not {"confidence", "reason", "status", "checker", "check_me"} & set(rows[0])
    assert "describes the activity" not in gold.to_csv(rows), "the checker's why is not printed"


def test_the_csv_reads_back_with_the_same_columns_and_one_row_a_page(pages):
    text = gold.to_csv(gold.sheet(pages, pages.t, base.BAND, 3))
    back = list(csv.DictReader(io.StringIO(text)))
    assert len(back) == 3 and back[0]["code"] and list(back[0])[-2:] == ["verdict", "what_is_wrong"]


def test_a_page_with_no_draft_is_not_on_the_sheet(pages):
    _act(
        pages,
        "KX-9",
        "Wholly the school's",
        strand="Block Room",
        materials="m",
        **{p: "x" for p in PAGE_PARTS},
    )
    assert "KX-9" not in {r["code"] for r in gold.sheet(pages, pages.t, base.BAND, 50)}


def test_a_draft_nobody_has_applied_yet_is_on_the_sheet_with_the_schools_words_beside_it(conn):
    """The first dev run recorded 99 drafts and applied none: the sheet reads the ledger, not only the applied pages."""
    _act(conn, "KX-1", "A", strand="Block Room", materials="m", objective="the school's own")
    run(
        conn,
        Scripted(
            {
                ("k2_page_draft", "KX-1"): [drafted(objective="x")],
                ("k2_page_check", "KX-1"): [AGREE],
            }
        ),
    )
    (row,) = gold.sheet(conn, conn.t, base.BAND, 5)
    assert row["objective"] == "the school's own" and row["objective_by"] == "school"
    assert row["steps_by"] == "drafted" and row["steps"], (
        "nothing was applied, the draft is read from the ledger"
    )


def test_a_draft_that_was_turned_down_is_not_on_the_sheet(conn):
    _act(conn, "KX-1", "A", strand="Block Room", materials="m")
    run(
        conn,
        Scripted({("k2_page_draft", "KX-1"): [drafted()], ("k2_page_check", "KX-1"): [AGREE]}),
    )
    assert gold.sheet(conn, conn.t, base.BAND, 5)
    (p,) = map_ledger.standing(conn, conn.t)
    map_ledger.settle(conn, conn.t, p["id"], False, conn.staff, "no") if p["now"] == "needs_person" else None
    map_ledger.apply(conn, conn.t, conn.staff, True)
    map_ledger.revert(conn, conn.t, p["id"], conn.staff, "taken back")
    assert gold.sheet(conn, conn.t, base.BAND, 5) == []


def test_the_command_writes_to_the_file_it_is_told_and_prints_no_text_of_the_sheet(
    conn, tmp_path, monkeypatch
):
    """A run's output is a public log: the sheet goes to a file, and what is printed is a count."""
    from typer.testing import CliRunner

    from engine.cli import app

    _act(conn, "KX-1", "A", strand="Block Room", materials="two secret boxes")
    run(conn, Scripted({("k2_page_draft", "KX-1"): [drafted()], ("k2_page_check", "KX-1"): [AGREE]}))
    monkeypatch.setattr(gold, "config", lambda: {"band": base.BAND})

    class Shared:
        """The test's own open connection, which the command may neither close nor switch to read-only mid-way."""

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def __getattr__(self, name):
            return getattr(conn, name)

        read_only = True

    monkeypatch.setattr(gold.db, "connect", lambda: Shared())
    out = tmp_path / "sheet.csv"
    done = CliRunner().invoke(app, ["curriculum", "gold-sheet", "--out", str(out)])
    assert done.exit_code == 0, done.output
    assert "secret" not in done.output and "KX-1" not in done.output and "wrote 1 pages" in done.output
    assert "two secret boxes" in out.read_text()
    assert CliRunner().invoke(app, ["curriculum", "gold-sheet"]).exit_code != 0, "no --out, no sheet"
