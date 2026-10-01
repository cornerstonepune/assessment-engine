"""Every page, route and action checks who is asking (goals/p0-every-page-checks-who-asks.yaml).

The code review of 2026-09-30 found nine pages that relied on their layout alone for the staff check. Next 16's own
guide (node_modules/next/dist/docs/01-app/02-guides/authentication.md, "Layouts and auth checks"): a layout does not
re-render on navigation, and does not stop the rest of the route rendering into the RSC payload. So every page, route
handler and server action checks the session itself, and `proxy.ts` turns away a request with no good session cookie
before anything renders.
"""

import re

import pytest

from engine.core import db

WEB = db.REPO_ROOT / "apps" / "web"
APP = WEB / "app"
CHECKS = re.compile(r"\b(?:requireStaff|currentStaff)\(")
OPEN_PAGES = {"app/login/page.tsx"}  # the one page anyone may open
OPEN_ACTIONS = {"lib/auth-actions.ts::signIn", "lib/auth-actions.ts::signOut"}

pytestmark = pytest.mark.skipif(not WEB.exists(), reason="the website is not beside the engine here")


def _rel(p):
    return str(p.relative_to(WEB))


def _unchecked(name):
    return [
        _rel(p)
        for p in sorted(APP.rglob(name))
        if _rel(p) not in OPEN_PAGES and not CHECKS.search(p.read_text())
    ]


def test_every_page_checks_who_is_asking():
    assert _unchecked("page.tsx") == []


def test_every_route_checks_who_is_asking():
    assert _unchecked("route.ts") == []


def test_every_server_action_checks_who_is_asking():
    unchecked, seen = [], 0
    for p in sorted([*APP.rglob("*actions.ts"), *WEB.joinpath("lib").glob("*actions.ts")]):
        src = p.read_text()
        if not src.lstrip().startswith('"use server"'):
            continue
        for name, body in re.findall(r"^export async function (\w+)\((.*?)(?=^export |\Z)", src, re.M | re.S):
            seen += 1
            if f"{_rel(p)}::{name}" not in OPEN_ACTIONS and not CHECKS.search(body):
                unchecked.append(f"{_rel(p)}::{name}")
    assert seen > 20, "found too few server actions; the search reads nothing"
    assert unchecked == []


def test_a_proxy_turns_away_a_request_without_a_good_session_before_it_renders():
    proxy = WEB / "proxy.ts"
    assert proxy.exists(), "no proxy.ts: nothing checks a request before the route renders"
    src = proxy.read_text()
    assert re.search(r"^export (?:async )?function proxy\(", src, re.M)
    assert "sessionEmail(" in src, "the proxy does not verify the session cookie's signature"
    (matcher,) = re.findall(r'matcher:\s*\[\s*"([^"]+)"\s*\]', src)
    # everything but sign-in and Next's own static files goes through it
    assert matcher.startswith("/((?!") and "login" in matcher and "_next/static" in matcher
    assert "api" not in matcher.split(")")[0], "the API routes are left out of the proxy"
