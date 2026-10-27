"""Question types, each a row, and the one approval that opens a type everywhere (goals/b2-question-types-are-rows.yaml,
ADR 0077, decisions B2-1, B2-2 and B2-4).

A type is what ADR 0077 calls a format: the printed format where the template is only the level's numbers written as a
name, else the template. Its row (`question_type`) holds its words, how it reaches the child and how it is marked; the
database puts every question in one (`question_type_of`). One approval, the coordinator's, covers a type in every skill
and level that uses it; a paper draws only questions of approved types at confirmed levels (`drawable_item`). There is
no page for it yet (B2-2): `engine types` lists them, `engine types approve` approves.
"""

from typing import Any

import typer

from engine.core import db

types_app = typer.Typer(help="The question types, their words and whether each waits for the coordinator")


def _tenant(conn: db.Conn) -> Any:
    return db.one(conn, "select id from tenant where slug = %s", (db.tenant_slug(),))["id"]


def state(conn: db.Conn, code: str) -> dict[str, Any]:
    """{approved, by, at} for one type: its first approval, or none."""
    row = conn.execute(
        "select approved_by as by, approved_at as at from question_type_approval"
        " where tenant_id = %s and question_type = %s order by approved_at limit 1",
        (_tenant(conn), code),
    ).fetchone()
    return {"approved": bool(row), "by": row and row["by"], "at": row and row["at"]}


def words(conn: db.Conn, code: str) -> str:
    """A type in the school's words."""
    row = conn.execute(
        "select words from question_type where tenant_id = %s and code = %s", (_tenant(conn), code)
    ).fetchone()
    return row["words"] if row else code


def approve(conn: db.Conn, code: str, by: str) -> dict[str, Any]:
    """`by` approves `code` in every skill and level that uses it. Approving it again changes nothing."""
    if not by.strip():
        raise ValueError("an approval names who gave it")
    tenant = _tenant(conn)
    if not conn.execute(
        "select 1 from question_type where tenant_id = %s and code = %s", (tenant, code)
    ).fetchone():
        raise LookupError(f"no question type {code}")
    if not state(conn, code)["approved"]:
        conn.execute(
            "insert into question_type_approval (tenant_id, question_type, approved_by) values (%s, %s, %s)",
            (tenant, code, by.strip()),
        )
    return state(conn, code)


def waiting(conn: db.Conn, skill: str, level: str) -> list[str]:
    """The types a level uses that wait for the coordinator."""
    return [
        r["question_type"]
        for r in conn.execute(
            "select l.question_type from skill_level_question_type l where l.tenant_id = %s and l.skill_code = %s"
            " and l.difficulty = %s and not exists (select 1 from question_type_approval a"
            "   where a.tenant_id = l.tenant_id and a.question_type = l.question_type) order by 1",
            (_tenant(conn), skill, level),
        )
    ]


def why_not(conn: db.Conn, skill: str, level: str) -> str:
    """Why a level gives a paper fewer questions than its bank holds, in words: its level is not confirmed, a type it
    uses waits for the coordinator, or an educator stopped one (retire.py). Empty when none."""
    out = []
    confirmed = conn.execute(
        "select confirmed_at from skill_level where tenant_id = %s and skill_code = %s and difficulty = %s",
        (_tenant(conn), skill, level),
    ).fetchone()
    if confirmed and not confirmed["confirmed_at"]:
        out.append(f"{skill} at {level} is not confirmed yet")
    out += [f"{words(conn, t)} ({t}) waits for the coordinator" for t in waiting(conn, skill, level)]
    out += [
        f"{words(conn, r['question_type'])} ({r['question_type']}) was stopped by an educator"
        for r in conn.execute(
            "select question_type from kind_stopped where tenant_id = %s and skill_code = %s and difficulty = %s"
            " order by 1",
            (_tenant(conn), skill, level),
        )
    ]
    return "; ".join(out)


@types_app.callback(invoke_without_command=True)
def show(ctx: typer.Context) -> None:
    """Every type: its code, its words, how many levels use it, and who approved it or that it waits."""
    if ctx.invoked_subcommand:
        return
    with db.connect() as conn:
        rows = conn.execute(
            "select t.code, t.words, (select count(*) from skill_level_question_type l where l.tenant_id = t.tenant_id"
            "   and l.question_type = t.code)::int as levels, a.approved_by"
            " from question_type t left join lateral (select approved_by from question_type_approval a"
            "   where a.tenant_id = t.tenant_id and a.question_type = t.code order by approved_at limit 1) a on true"
            " where t.tenant_id = %s order by t.code",
            (_tenant(conn),),
        ).fetchall()
    for r in rows:
        said = f"approved by {r['approved_by']}" if r["approved_by"] else "waits for the coordinator"
        typer.echo(f"  {r['code']:<30} {r['words']:<32} levels {r['levels']:>3}  {said}")
    typer.echo(f"  {len(rows)} types, {sum(1 for r in rows if not r['approved_by'])} waiting")


@types_app.command("approve")
def approve_command(
    code: str,
    by: str = typer.Option(..., "--by", help="the coordinator who approves it"),
    dry_run: bool = typer.Option(False, "--dry-run", help="say what would be approved; write nothing"),
) -> None:
    """Approve one question type in every skill and level that uses it."""
    with db.connect() as conn:
        try:
            had = state(conn, code)["approved"]
            s, said = approve(conn, code, by), words(conn, code)
        except (ValueError, LookupError) as e:
            typer.echo(str(e), err=True)
            raise typer.Exit(1) from e
        if dry_run:
            conn.rollback()
        else:
            conn.commit()
    did = "already approved" if had else "would be approved" if dry_run else "approved"
    typer.echo(f"{code} ({said}) {did} by {s['by']}")
