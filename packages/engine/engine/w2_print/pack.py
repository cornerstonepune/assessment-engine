"""W2/N7 — the teacher approves a pack, and only then does it print as one.

A pack is every paper made for one class, one week and one purpose — class practice, class assessment, or
the children's own next papers sent home (`focus`) — with its spares. The engine makes it; a person
approves it in their name; the pack PDF is the approved papers exactly as each was rendered, in handout
order (roll order, spares last), merged. Nothing here draws a page again: what prints is what was made.
"""

from pathlib import Path

import pymupdf

# The papers in one pack. A paper handed out from the library, or a child's next paper, knows its own week,
# class and purpose; a paper generated before step 7 is found, as it always was, through its template's week.
_IN_PACK = (
    "((si.week = %(week)s and si.section = %(section)s and si.kind = %(kind)s)"
    " or si.sheet_template_id in ("
    "   select st.id from sheet_template st left join child c on c.id = st.child_id"
    "   where st.source = 'generated' and st.week = %(week)s and (c.section = %(section)s or st.child_id is null)))"
)


def approve(conn, section: str, week: str, kind: str = "practice", by: str = "") -> dict:
    """A person says the pack may be printed, and their name goes on every paper in it.

    One tap for a class: the teacher's attention is the scarcest thing in the school, so this is per pack
    and not per sheet. The database refuses a printed sheet with no approver
    (`sheet_instance_printed_needs_approver`), which is what makes this a gate and not a label.
    """
    if not by:
        raise ValueError("an approval must name a person — that is the whole point of it")
    rows = conn.execute(
        "update sheet_instance si set print_status = 'printed', printed_at = now(),"
        " approved_by = %(by)s, approved_at = now(), updated_at = now()"
        f" where si.print_status = 'new' and {_IN_PACK}"
        " returning si.qr_code, si.child_id",
        {"by": by, "week": week, "section": section, "kind": kind},
    ).fetchall()
    return {
        "section": section,
        "week": week,
        "kind": kind,
        "approved_by": by,
        "sheets": len(rows),
        "named": sum(1 for r in rows if r["child_id"]),
        "spares": sum(1 for r in rows if not r["child_id"]),
        "qr_codes": [r["qr_code"] for r in rows],
    }


def papers(conn, section: str, week: str, kind: str) -> list[dict]:
    """The pack in handout order: each child's paper by roll number, then the spares."""
    return conn.execute(
        "select si.qr_code, si.child_id, c.roll_no, si.print_status, si.approved_by, si.pdf_path"
        " from sheet_instance si left join child c on c.id = si.child_id"
        f" where si.print_status <> 'void' and {_IN_PACK}"
        " order by si.child_id is null,"
        "   coalesce(nullif(regexp_replace(c.roll_no, '\\D', '', 'g'), '')::int, 9999), c.roll_no, si.qr_code",
        {"week": week, "section": section, "kind": kind},
    ).fetchall()


def pdf(conn, section: str, week: str, kind: str, outdir: Path) -> Path:
    """The approved pack as one PDF. Refuses, in words, a pack still waiting for a teacher or one whose
    papers were never rendered — a pack with a hole in it is not the pack."""
    rows = papers(conn, section, week, kind)
    if not rows:
        raise LookupError(f"no papers for {section} · {week} · {kind}")
    waiting = [r["qr_code"] for r in rows if r["print_status"] == "new"]
    if waiting:
        raise PermissionError(
            f"{len(waiting)} papers in this pack wait for a teacher's approval; nothing prints before"
        )
    missing = [r["qr_code"] for r in rows if not r["pdf_path"] or not Path(r["pdf_path"]).exists()]
    if missing:
        raise FileNotFoundError(f"not rendered on this machine: {', '.join(missing)}")
    return merge([r["pdf_path"] for r in rows], Path(outdir) / f"{section}-{week}-{kind}.pdf")


def merge(pdfs: list, out: Path) -> Path:
    """Papers as printed, one after another, as one PDF."""
    out.parent.mkdir(parents=True, exist_ok=True)
    with pymupdf.open() as merged:
        for path in pdfs:
            with pymupdf.open(path) as one:
                merged.insert_pdf(one)
        merged.save(out)
    return out
