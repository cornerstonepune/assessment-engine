"""What is wrong on live now: `engine live watch`, asked every ten minutes by .github/workflows/watch-live.yml from
outside the server, so Nimish hears of a problem from the system and not from an educator
(goals/p2-live-is-watched.yaml).

One line per problem; none is all well. The lines go to an issue on a public repository, so they hold counts, flow
names and page patterns only: never a run's error text (it can carry a child's name), an id, or an address. The
limits are threshold rows.
"""

import os

from engine.checks import rules
from engine.core import db


def problems(conn: db.Conn, free_bytes: int) -> list[str]:
    """Every problem live has now. `free_bytes` is what the server's disk has free."""
    rows = conn.execute("select key, value from threshold where key like 'watch.%'").fetchall()
    limit = {r["key"]: float(r["value"]) for r in rows}
    stuck, window, floor = (
        int(limit["watch.stuck_minutes"]),
        int(limit["watch.window_minutes"]),
        limit["watch.disk_free_gb"],
    )
    out = [
        f"{r['flow']} runs still running after {stuck} minutes: {r['n']}"
        for r in conn.execute(
            "select flow, count(*) as n from flow_run where status = 'running'"
            " and started_at < now() - make_interval(mins => %s) group by flow order by flow",
            (stuck,),
        )
    ]
    out += [
        f"{r['flow']} runs failed in the last {window} minutes: {r['n']}"
        for r in conn.execute(
            "select flow, count(*) as n from flow_run where status = 'error'"
            " and finished_at > now() - make_interval(mins => %s) group by flow order by flow",
            (window,),
        )
    ]
    out += [
        f"website errors on {r['route']} in the last {window} minutes: {r['n']}"
        for r in conn.execute(
            "select route, count(*) as n from web_error where created_at > now() - make_interval(mins => %s)"
            " group by route order by route",
            (window,),
        )
    ]
    # a rule live holds otherwise than the migrations make it (goals/l3b-live-says-what-went-wrong.yaml): the first
    # few by name, and how many in all
    drifted = rules.drift(conn)
    out += [f"a database rule is not the migrations': {d}" for d in drifted[:5]]
    if len(drifted) > 5:
        out.append(f"and {len(drifted) - 5} more database rules are not the migrations'")
    if free_bytes < floor * 10**9:
        out.append(f"the server's disk has {free_bytes / 10**9:.1f} GB free, less than {floor:g} GB")
    # A "set your password" email that never left: the sender is not configured in Vercel, or it refused. The rows
    # carry the word alone, never an address or a reason (goals/auth-email-password.yaml), so this line can go to a
    # public issue as the rest do.
    mail_window = int(limit.get("watch.mail_window_minutes", 1440))
    said = {
        "not configured": "mail is not configured, so {n} set-password links of the last {mins} minutes were never sent",
        "failed": "the mail sender refused {n} set-password links of the last {mins} minutes",
        "not recorded": "{n} set-password links of the last {mins} minutes say nothing of their email",
    }
    out += [
        said[r["mail"]].format(n=r["n"], mins=mail_window)
        for r in conn.execute(
            "select coalesce(mail, 'not recorded') as mail, count(*) as n from password_link"
            " where mail is distinct from 'sent' and created_at > now() - make_interval(mins => %s)"
            " group by 1 order by 1",
            (mail_window,),
        )
    ]
    if not os.environ.get("TYPESAFE_API_KEY"):  # the engine's own environment: the watch runs inside it
        out.append("Jev's key is missing on the engine: every judgement Jev makes goes to a person")
    return out
