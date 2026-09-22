"""`engine live check` reads what Vercel recorded; these pin how it counts (engine/live.py)."""

from engine.checks import live


def _r(path, status=200, level="info", message=""):
    return {"requestPath": path, "responseStatusCode": status, "level": level, "message": message}


def test_a_request_vercel_killed_counts_as_timed_out_not_as_failed():
    s = live.summarise(
        [_r("/library", 200, "error", "Vercel Runtime Timeout Error: Task timed out after 300 seconds")],
        ["/library"],
    )
    assert len(s["timed_out"]) == 1 and s["failed"] == []


def test_a_server_error_counts_as_failed():
    s = live.summarise([_r("/capture", 500, "error", "boom")], ["/capture"])
    assert len(s["failed"]) == 1 and s["timed_out"] == []


def test_a_page_is_seen_only_when_it_was_served_and_the_root_only_by_itself():
    s = live.summarise(
        [_r("/library?set=A"), _r("/skill-sets/R5"), _r("/growth", 500)],
        ["/", "/library", "/skill-sets", "/growth"],
    )
    assert s["seen"] == ["/library", "/skill-sets"]


def test_the_window_is_minutes_or_hours():
    assert live._window("45m").total_seconds() == 2700
    assert live._window("2h").total_seconds() == 7200
