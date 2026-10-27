"""Measure the harness itself: which components fired, and whether the repository is healthy.

Used by `athena scorecard`, `athena health` and the nightly health_issue.py. Standard library only.
Reads the component register (.claude/athena/components.json), the session transcripts under
$HOME/.claude/projects, the plan-usage files under $HOME/.athena/usage and usage/review-status.json.
"""
import json
import os
import statistics
from datetime import datetime, timedelta, timezone
from pathlib import Path

MEASURED = ("skill", "agent", "plugin", "hook")  # kinds whose firing shows up in session transcripts
IDLE_DAYS = 14
MAX_CLAUDE_MD, MAX_AGENTS_MD, MAX_HANDOFF, MAX_LESSONS = 200, 100, 50, 30
STUCK_DAYS, LEDGER_DAYS = 7, 7
STUCK_STATES = ("draft", "locked", "building", "blocked")


def now():
    return datetime.now(timezone.utc)


def parse_ts(s):
    try:
        d = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def read_json(p):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return {}


# ---------------------------------------------------------------- register
def register(root):
    """The repo's installed register, else the one that ships next to this script."""
    for p in (Path(root) / ".claude" / "athena" / "components.json", Path(__file__).resolve().parent.parent / "components.json"):
        if p.exists():
            return read_json(p).get("components", [])
    return []


# ---------------------------------------------------------------- transcripts
def transcript_files(home):
    base = Path(home) / ".claude" / "projects"
    return sorted(base.glob("*/*.jsonl")) + sorted(base.glob("*/*/subagents/*.jsonl"))


def events(home):
    """One tuple per thing a session did: (kind, name, session, timestamp, tokens)."""
    out, seen = [], set()
    for f in transcript_files(home):
        for line in f.read_text(errors="replace").splitlines():
            try:
                row = json.loads(line)
            except ValueError:
                continue
            ts, sid = parse_ts(row.get("timestamp")), row.get("sessionId") or f.stem
            att = row.get("attachment")
            if isinstance(att, dict) and str(att.get("type", "")).startswith("hook"):
                out.append(("hook", f"{att.get('hookName', '')} {att.get('command', '')}", sid, ts, 0))
                continue
            msg = row.get("message")
            if not isinstance(msg, dict) or not isinstance(msg.get("content"), list):
                continue
            u = msg.get("usage") or {}
            tokens = sum(int(u.get(k) or 0) for k in ("input_tokens", "output_tokens", "cache_creation_input_tokens"))
            for part in msg["content"]:
                if not (isinstance(part, dict) and part.get("type") == "tool_use"):
                    continue
                inp = part.get("input") or {}
                tool = part.get("name", "")
                mid = msg.get("id")
                if mid and mid in seen:  # a message is written as several lines that repeat its usage: charge it once
                    tokens = 0
                seen.add(mid)
                if tool == "Skill":
                    out.append(("skill", str(inp.get("skill", "")), sid, ts, tokens))
                elif tool in ("Agent", "Task"):
                    out.append(("agent", str(inp.get("subagent_type", "")), sid, ts, tokens))
                elif tool.startswith("mcp__"):
                    out.append(("tool", tool, sid, ts, tokens))
    return out


def matches(comp, ev):
    kind, name = comp["kind"], comp["name"]
    ekind, ename = ev[0], ev[1]
    if kind == "skill":
        return ekind == "skill" and (ename == name or ename.endswith(":" + name))
    if kind == "agent":
        return ekind == "agent" and (ename == name or ename.endswith(":" + name))
    if kind == "plugin":
        return (ekind == "skill" and ename.startswith(name + ":")) or \
               (ekind == "tool" and f"plugin_{name}" in ename) or (ekind == "hook" and name in ename)
    if kind == "hook":
        return ekind == "hook" and any(m in ename for m in comp.get("match", [name]))
    return False


def review_status(root):
    return (read_json(Path(root) / "usage" / "review-status.json") or {}).get("reviews", {})


def collect(root, home):
    """component name -> {fired, sessions, tokens, last}. `last` is a datetime or None."""
    evs = events(home)
    reviews = review_status(root)
    rows = {}
    for c in register(root):
        hit = [e for e in evs if matches(c, e)] if c["kind"] in MEASURED else []
        last = max((e[3] for e in hit if e[3]), default=None)
        fired = len(hit)
        if c["kind"] == "task" and c["name"] in reviews:
            fired, last = 1, parse_ts(reviews[c["name"]].get("last_run"))
        rows[c["name"]] = {"kind": c["kind"], "fired": fired, "sessions": len({e[2] for e in hit}),
                           "tokens": sum(e[4] for e in hit), "last": last,
                           "idle_days": int(c.get("idle_days", IDLE_DAYS)), "measured": c["kind"] in MEASURED}
    return rows


def has_records(home):
    return bool(transcript_files(home))


# ---------------------------------------------------------------- scorecard
TIER_BUDGET_MIN = {0: 5, 1: 10, 2: 20}  # median CI minutes a tier may take; tier 3 has no budget


def tier_lines(path):
    """One line per tier: the median CI minutes of that tier's newest 20 pull requests, RED when over budget."""
    try:
        records = json.loads(Path(path).read_text())
    except Exception:
        return []
    if not records:
        return []
    lines = ["", "CI time by tier (median minutes of the newest 20 pull requests):"]
    for tier in range(4):
        newest = sorted((r for r in records if r["tier"] == tier), key=lambda r: r["merged_at"])[-20:]
        if not newest:
            continue
        med = statistics.median(r["ci_minutes"] for r in newest)
        budget = TIER_BUDGET_MIN.get(tier)
        flag = f"  RED: budget is {budget} min" if budget is not None and med > budget else \
            ("  (no budget)" if budget is None else "")
        lines.append(f"tier {tier}: median {med:.1f} min over {len(newest)} pull requests{flag}")
    return lines


def scorecard(root, home):
    rows = collect(root, home)
    lines = [f"{'component':34} {'kind':7} {'fired':>5} {'sessions':>8} {'cost (tokens)':>14}  last fired"]
    for name, r in sorted(rows.items(), key=lambda kv: (kv[1]["kind"], kv[0])):
        if r["measured"] or r["kind"] == "task":
            last = r["last"].date().isoformat() if r["last"] else "never"
            lines.append(f"{name:34} {r['kind']:7} {r['fired']:>5} {r['sessions']:>8} {r['tokens']:>14}  {last}")
        else:
            lines.append(f"{name:34} {r['kind']:7} {'-':>5} {'-':>8} {'-':>14}  not measured here (runs in CI)")
    if os.environ.get("ATHENA_PR_TIMES"):
        lines += tier_lines(os.environ["ATHENA_PR_TIMES"])
    return "\n".join(lines)


# ---------------------------------------------------------------- health
def line_count(p):
    try:
        return len(Path(p).read_text().splitlines())
    except OSError:
        return 0


def usage_dir(home):
    return Path(home) / ".athena" / "usage"


def newest_ledger_ts(home):
    best = None
    for f in usage_dir(home).glob("2*.jsonl"):
        for line in f.read_text(errors="replace").splitlines():
            try:
                t = parse_ts(json.loads(line).get("ts"))
            except ValueError:
                continue
            if t and (best is None or t > best):
                best = t
    return best


def health(root, home, version, env=None):
    """Return a list of (status, text). status is PASS, FAIL or SKIP."""
    env, root, res = env if env is not None else os.environ, Path(root), []
    ci = env.get("ATHENA_HEALTH_CI") == "1"  # set only by the nightly workflow; GitHub cannot see Mac sessions
    add = lambda ok, text: res.append(("PASS" if ok else "FAIL", text))

    cfg = read_json(root / ".claude" / "athena" / "config.json")
    handoff = (cfg.get("own_loop") or {}).get("handoff") or "docs/HANDOFF.md"  # a repo with its own loop keeps its own
    have = read_json(root / ".claude" / "athena" / "MANIFEST.json").get("athena")
    add(have == version, f"harness version {have or 'not installed'} (latest {version})")
    for rel, cap in (("CLAUDE.md", MAX_CLAUDE_MD), ("AGENTS.md", MAX_AGENTS_MD), (handoff, MAX_HANDOFF)):
        n = line_count(root / rel)
        add(n <= cap, f"{rel} has {n} lines (limit {cap})")
    lessons = sum(1 for l in (root / "docs/athena/learnings.md").read_text().splitlines() if l.lstrip().startswith("- ")) \
        if (root / "docs/athena/learnings.md").exists() else 0
    add(lessons <= MAX_LESSONS, f"{lessons} lessons loaded (limit {MAX_LESSONS})")

    stuck = []
    for d in sorted((root / "specs").glob("*/status.json")) if (root / "specs").is_dir() else []:
        s = read_json(d)
        t = parse_ts(s.get("updated_at"))
        if s.get("status") in STUCK_STATES and t and now() - t > timedelta(days=STUCK_DAYS):
            stuck.append(f"{d.parent.name} ({s['status']}, {(now() - t).days} days)")
    add(not stuck, "specs stuck over %d days: %s" % (STUCK_DAYS, ", ".join(stuck) or "none"))

    reviews = review_status(root)
    if reviews or (root / "usage").is_dir():
        bad = [n for n, r in reviews.items() if r.get("status") != "success"]
        add(not bad, "scheduled reviews: " + (("last run failed: " + ", ".join(bad)) if bad else "all last runs succeeded"))
    else:
        res.append(("PASS", "scheduled reviews: none kept in this repository"))

    mode = read_json(root / ".claude" / "settings.json").get("env", {}).get("WINNOW_MODE", "not set")
    res.append(("PASS", f"Jev mode: {mode}"))
    if ci:  # the Jev key, the usage files and the sessions live on the Mac, which GitHub cannot see
        res.append(("SKIP", "Jev key, usage ledger and plan usage are checked on the Mac, not on GitHub"))
    else:
        add(bool(env.get("TYPESAFE_API_KEY")), "Jev key " + ("present" if env.get("TYPESAFE_API_KEY") else "missing"))
        led = newest_ledger_ts(home)
        add(bool(led and now() - led < timedelta(days=LEDGER_DAYS)),
            "usage ledger last written " + (led.date().isoformat() if led else "never") + f" (limit {LEDGER_DAYS} days)")
        latest = read_json(usage_dir(home) / "latest.json")
        wk = latest.get("seven_day")
        add(isinstance(wk, (int, float)) and not isinstance(wk, bool),
            "plan usage " + (f"recorded ({wk}% this week)" if isinstance(wk, (int, float)) else
                             "not recorded: " + str(latest.get("seven_day_reason") or "no reading")))
    if not has_records(home):
        res.append(("SKIP", "idle components: no session records on this machine"))
    else:
        idle = []
        for name, r in sorted(collect(root, home).items()):
            if r["measured"] and (r["last"] is None or now() - r["last"] > timedelta(days=r["idle_days"])):
                idle.append(f"{name} ({'never fired' if r['last'] is None else 'last ' + r['last'].date().isoformat()})")
        add(not idle, "components idle past their limit: " + (", ".join(idle) or "none"))
    return res


def render(results):
    return "\n".join(f"{s} {t}" for s, t in results)
