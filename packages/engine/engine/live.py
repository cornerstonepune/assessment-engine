"""Is the live website answering? Read from what the platforms themselves recorded.

A local test run can be green while the public address hangs (ADR 0024), so a step is closed on
evidence from the live link: Vercel's log of every production request and Supabase's log of the
live database. Nothing here sends a request to the website; it only reads what happened in a window
in which a person used it.
"""

import json
import subprocess
import urllib.parse
import urllib.request
from datetime import UTC, datetime, timedelta

from engine import db

MENU = ("/", "/worksheets", "/library", "/capture", "/growth", "/home")
WEB = db.REPO_ROOT / "apps" / "web"


def _window(since: str) -> timedelta:
    n, unit = int(since[:-1]), since[-1]
    return {"m": timedelta(minutes=n), "h": timedelta(hours=n)}[unit]


def vercel_requests(since: str) -> list[dict]:
    """Every production request Vercel logged in the window, one row per request. Its log repeats a
    request's line many times; a request is its `id`."""
    p = subprocess.run(
        ["vercel", "logs", "--environment", "production", "--no-branch", "--since", since,
         "--limit", "5000", "--json"],
        cwd=WEB, capture_output=True, text=True, timeout=180, check=True,
    )  # fmt: skip
    rows = {}
    for line in p.stdout.splitlines():
        if line.startswith("{"):
            r = json.loads(line)
            if r.get("source") != "static":
                rows.setdefault(r["id"], r)
    return list(rows.values())


def database_events(since: str) -> tuple[int, float]:
    """(statement timeouts, slowest checkpoint in seconds) in the live database over the window,
    from Supabase's own log of it."""
    end = datetime.now(UTC)
    start = end - _window(since)
    query = (
        "select event_message from postgres_logs where event_message like 'checkpoint complete%'"
        " or event_message like '%statement timeout%' limit 1000"
    )
    url = (
        f"https://api.supabase.com/v1/projects/{db.env('SUPABASE_PROJECT_REF')}/analytics/endpoints/logs.all?"
        + urllib.parse.urlencode(
            {
                "iso_timestamp_start": f"{start:%Y-%m-%dT%H:%M:%SZ}",
                "iso_timestamp_end": f"{end:%Y-%m-%dT%H:%M:%SZ}",
                "sql": query,
            }
        )
    )
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {db.env('SUPABASE_ACCESS_TOKEN')}"})
    with urllib.request.urlopen(req, timeout=60) as res:
        events = json.load(res).get("result") or []
    timeouts = sum("statement timeout" in e["event_message"] for e in events)
    slowest = max(
        (
            float(e["event_message"].split("total=")[1].split(" s")[0])
            for e in events
            if "total=" in e["event_message"]
        ),
        default=0.0,
    )
    return timeouts, slowest


def summarise(requests: list[dict], pages: list[str]) -> dict:
    """What a person needs from the window: how many requests, how many never finished, how many
    failed, and which of the pages asked about were served."""
    timed_out = [r for r in requests if "timed out" in (r.get("message") or "")]
    failed = [
        r
        for r in requests
        if r not in timed_out
        and ((r.get("responseStatusCode") or 0) >= 500 or r.get("level") in ("error", "fatal"))
    ]
    served = {r["requestPath"].split("?")[0] for r in requests if r.get("responseStatusCode") == 200}
    seen = [p for p in pages if any(s == p if p == "/" else s.startswith(p) for s in served)]
    return {
        "requests": len(requests),
        "timed_out": timed_out,
        "failed": failed,
        "seen": seen,
    }


def check(since: str, pages: list[str]) -> tuple[bool, list[str]]:
    menu = not pages
    pages = list(MENU) if menu else pages
    s = summarise(vercel_requests(since), pages)
    timeouts, slowest = database_events(since)
    what = "menu pages" if menu else "pages"
    lines = [
        f"live, last {since}: {s['requests']} requests · {len(s['timed_out'])} timed out · "
        f"{len(s['failed'])} failed · {len(s['seen'])} of {len(pages)} {what} seen",
        f"  database: {timeouts} statement timeouts · slowest checkpoint {slowest:.1f} s",
    ]
    lines += [f"  not seen: {p}" for p in pages if p not in s["seen"]]
    lines += [f"  timed out: {r['requestPath']}" for r in s["timed_out"]]
    lines += [
        f"  failed: {r['requestPath']} {r.get('responseStatusCode')} {(r.get('message') or '')[:120]}"
        for r in s["failed"]
    ]
    ok = not s["timed_out"] and not s["failed"] and len(s["seen"]) == len(pages)
    return ok, lines
