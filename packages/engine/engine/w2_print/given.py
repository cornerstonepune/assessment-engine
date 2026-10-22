"""W2/N7 — an assessment given out: the educator's word that it was given, and on which day; and a child who was away.

The scope Nimish locked on 2026-10-22 (S2, goals/s2-the-assessment-card.yaml): an educator presses "Given on" with
the date; an upload without it is still accepted ("no rules, no chasing"). A child away that day has their paper
carried: it is not counted missing, and is read whenever it comes back.

Each is the person's word, kept as a run of its own (`flow_run`, flow `given` or `absent`), never a change to the
paper: a later word is a new row and the newest stands, as a correction does (rule 4's way). Codes and the person's
email only, never a name (rule 6).
"""

import json
from datetime import date

GIVEN, ABSENT = "given", "absent"


def _papers(conn, qrs: list[str]) -> list[str]:
    """The printed codes named that are papers of this school and not void, in the order given."""
    found = {
        r["qr"]
        for r in conn.execute(
            "select qr_code as qr from sheet_instance where qr_code = any(%s) and print_status <> 'void'",
            (qrs,),
        ).fetchall()
    }
    return [q for q in dict.fromkeys(qrs) if q in found]


def _keep(conn, tenant, flow: str, by: str, said: str, request: dict) -> str:
    return str(
        conn.execute(
            # the clock's own time, not the transaction's: two words said in one transaction stay in the order said,
            # and the newest stands
            "insert into flow_run (tenant_id, flow, trigger, status, started_at, finished_at, request) values"
            " (%s, %s, %s, 'ok', clock_timestamp(), clock_timestamp(), %s::jsonb) returning id",
            (tenant, flow, f"{by}: {said}", json.dumps(request)),
        ).fetchone()["id"]
    )


def given(conn, tenant, qrs: list[str], on: date, by: str) -> dict:
    """The educator says these papers were given on `on`. Refused, in words, for no person, a day still to come, or
    no paper of this school among the codes."""
    if not by:
        raise ValueError("say who gave the papers")
    # the school's own day, not the server's: just after midnight in Pune, a server on UTC is still on yesterday
    if on > conn.execute("select (now() at time zone 'Asia/Kolkata')::date as d").fetchone()["d"]:
        raise ValueError(f"{on.isoformat()} is still to come: say the day the papers were given")
    papers = _papers(conn, qrs)
    if not papers:
        raise LookupError("none of these codes is a paper of this school")
    run = _keep(
        conn, tenant, GIVEN, by, f"given on {on.isoformat()}", {"qrs": papers, "on": on.isoformat(), "by": by}
    )
    return {"run": run, "papers": len(papers), "on": on.isoformat()}


def absent(conn, tenant, qr: str, away: bool, by: str) -> dict:
    """The educator says the child whose paper this is was away (`away`), or is back: the newest word stands."""
    if not by:
        raise ValueError("say who says so")
    if not _papers(conn, [qr]):
        raise LookupError(f"{qr} is not a paper of this school")
    run = _keep(
        conn, tenant, ABSENT, by, f"{qr} {'away' if away else 'back'}", {"qr": qr, "away": away, "by": by}
    )
    return {"run": run, "qr": qr, "away": away}
