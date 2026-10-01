"""What is wrong on live now: `engine live watch`, asked every ten minutes by .github/workflows/watch-live.yml from
outside the server, so Nimish hears of a problem from the system and not from an educator
(goals/p2-live-is-watched.yaml).

One line per problem; none is all well. The lines go to an issue on a public repository, so they hold counts, flow
names and page patterns only: never a run's error text (it can carry a child's name), an id, or an address. The
limits are threshold rows.
"""

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
    if free_bytes < floor * 10**9:
        out.append(f"the server's disk has {free_bytes / 10**9:.1f} GB free, less than {floor:g} GB")
    return out
