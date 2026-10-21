"""What reaches live, and when (goals/p0-live-changes-wait-for-ci.yaml, goals/p0-papers-survive-a-deploy.yaml,
goals/l4-the-website-waits-for-the-database.yaml).

Both read the files that deploy, not a live run: the code review of 2026-09-30 found the engine rebuilt and the live
database migrated on every push to main while CI was still running, and every paper the engine had rendered gone
with the container each deploy recreated.
"""

import re
from pathlib import Path

import yaml

from engine.core import db

WORKFLOWS = db.REPO_ROOT / ".github" / "workflows"
LIVE = ("deploy-engine.yml", "migrate.yml")
GATED = "steps.plan.outputs.go == 'yes'"


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text())


def _on(spec: dict) -> dict:
    return spec.get("on", spec.get(True))  # YAML 1.1 reads the bare key `on` as true


def test_the_workflow_waited_for_is_ci():
    assert _load(WORKFLOWS / "ci.yml")["name"] == "ci"


def test_nothing_reaches_live_before_ci_passes_on_that_commit():
    for name in LIVE:
        spec = _load(WORKFLOWS / name)
        on = _on(spec)
        assert "push" not in on, f"{name} starts on a push, beside CI"
        assert on["workflow_run"] == {"workflows": ["ci"], "types": ["completed"], "branches": ["main"]}, name
        (job,) = spec["jobs"].values()
        assert "github.event.workflow_run.conclusion == 'success'" in job["if"], f"{name} runs on a red CI"
        assert "workflow_run.head_sha" in job["env"]["SHA"], f"{name} does not take the commit CI passed on"
        checkout = next(s for s in job["steps"] if s.get("uses", "").startswith("actions/checkout"))
        assert checkout["with"]["ref"] == "${{ env.SHA }}", f"{name} checks out main's newest instead"


def test_only_mains_newest_commit_changes_live():
    for name in LIVE:
        (job,) = _load(WORKFLOWS / name)["jobs"].values()
        steps = job["steps"]
        at = next(i for i, s in enumerate(steps) if s.get("id") == "plan")
        assert "git ls-remote origin refs/heads/main" in steps[at]["run"], (
            f"{name} never asks what main holds"
        )
        after = [s.get("name") or s.get("uses") for s in steps[at + 1 :] if GATED not in s.get("if", "")]
        assert after == [], f"{name} runs {after} even when a newer merge is on main"


def test_the_website_goes_live_only_once_live_has_the_commits_migrations():
    """Vercel holds each production deployment until the commit's `live database` status is green (Deployment Checks,
    ADR 0074); only migrate live sets it, on the commit it migrated, after `db push` — so a page never reaches a
    database that lacks its tables (2026-10-15: the site down 03:00–03:26 UTC while migrate live waited on CI)."""
    spec = _load(WORKFLOWS / "migrate.yml")
    (job,) = spec["jobs"].values()
    assert job["permissions"]["statuses"] == "write", "migrate live cannot set a commit's status"
    *_, push, said = job["steps"]
    assert "supabase db push" in push["run"], "the status is not set after the migration"
    assert said["if"] == f"!cancelled() && {GATED}", "the status is set for a commit main has moved on from"
    assert said["env"]["STATE"] == "${{ job.status == 'success' && 'success' || 'failure' }}"
    for needed in ("statuses/$SHA", 'context="live database"', 'state="$STATE"'):
        assert needed in said["run"], needed
    assert "live database" in (WORKFLOWS / "ci.yml").read_text(), (
        "ci.yml still says Vercel deploys on every merge"
    )


def test_the_engines_data_folder_is_on_the_servers_disk():
    # where the image's engine writes: REPO_ROOT is the folder holding `engine/`, so its data folder is /app/data
    dockerfile = (db.REPO_ROOT / "packages" / "engine" / "Dockerfile").read_text()
    runtime = dockerfile.split(" AS runtime", 1)[1]
    assert re.search(r"^WORKDIR /app$", runtime, re.M)
    assert re.search(r"^COPY engine \./engine$", runtime, re.M)
    inside = db._repo_root_for(Path("/app/engine/core/db.py")) / "data"
    assert inside == Path("/app/data")

    volumes = _load(db.REPO_ROOT / "deploy" / "compose.server.yml")["services"]["engine"]["volumes"]
    on_disk = [v for v in volumes if v.split(":")[1] == str(inside)]
    assert on_disk, "the engine's data folder lives in the container and goes with every rebuild"
    host, _, mode = on_disk[0].partition(":")
    assert host.startswith("${HOME}/") and not mode.endswith(":ro"), on_disk[0]


def test_live_is_watched_every_ten_minutes_from_outside_the_server():
    """watch-live.yml asks the engine what is wrong on the server, checks both public doors, and tells Nimish by an
    issue that mentions him; the server's address is masked, because the repository's logs are public
    (goals/p2-live-is-watched.yaml)."""
    spec = _load(WORKFLOWS / "watch-live.yml")
    assert _on(spec)["schedule"] == [{"cron": "*/10 * * * *"}]
    script = "\n".join(s.get("run", "") for s in spec["jobs"]["watch"]["steps"])
    for needed in (
        "engine live watch",
        "::add-mask::",
        "/health",
        "/login",
        "@nimishshah1989",
        "gh issue close",
    ):
        assert needed in script, needed
    assert spec["permissions"]["issues"] == "write"


def test_a_bad_deploy_is_undone_by_naming_an_earlier_commit():
    """Run by hand, the deploy takes the commit to roll back to and deploys exactly that (goals/p2-live-recovers.yaml)."""
    spec = _load(WORKFLOWS / "deploy-engine.yml")
    assert "commit" in _on(spec)["workflow_dispatch"]["inputs"]
    sha = spec["jobs"]["deploy"]["env"]["SHA"]
    assert "inputs.commit" in sha and sha.index("inputs.commit") < sha.index("github.sha")
    assert spec["jobs"]["deploy"]["steps"][0]["with"]["ref"] == "${{ env.SHA }}"


# goals/l8-deploy-without-downtime.yaml. Every deploy to 21 Oct 2026 stopped the engine, then started the new one: 23–31
# seconds of "The engine refused (502)" (measured on the deploy engine runs' own logs, docs/notes/l8-…md).
SWITCH = db.REPO_ROOT / "deploy" / "switch.sh"
FAKES = {
    # every call written down; `docker exec deploy-caddy-1 cat …` answers with the Caddyfile the folder holds
    "docker": 'echo "docker $*" >> "$LOG"\n'
    'if [ "$1 $2" = "exec deploy-caddy-1" ]; then cat "$CADDY_SEES"; fi\n',
    # /health answers 200, except on a port named in DOWN
    "curl": 'url="${@: -1}"; port="${url#http://127.0.0.1:}"; port="${port%%/*}"\n'
    'case " $DOWN " in *" $port "*) echo "curl $port 000" >> "$LOG"; printf 000 ;;'
    ' *) echo "curl $port 200" >> "$LOG"; printf 200 ;; esac\n',
    "sleep": "",
}


def _switch(tmp_path, down="", caddy_sees=None):
    """deploy/switch.sh run as the server runs it, with docker, curl and sleep that only write down what they were asked
    → (exit code, every call in order)."""
    import os
    import subprocess

    bin_ = tmp_path / "bin"
    bin_.mkdir()
    for name, body in FAKES.items():
        (bin_ / name).write_text("#!/usr/bin/env bash\n" + body)
        (bin_ / name).chmod(0o755)
    log = tmp_path / "calls"
    log.touch()
    seen = tmp_path / "caddy-sees"
    seen.write_text(caddy_sees if caddy_sees is not None else (SWITCH.parent / "Caddyfile").read_text())
    env = {**os.environ, "PATH": f"{bin_}:{os.environ['PATH']}", "LOG": str(log), "DOWN": down, "TRIES": "3"}
    env["CADDY_SEES"] = str(seen)
    done = subprocess.run(["bash", str(SWITCH)], cwd=SWITCH.parent, env=env, capture_output=True, text=True)
    return done.returncode, log.read_text().splitlines()


def _at(calls, start):
    return next(i for i, c in enumerate(calls) if c.startswith(start))


def test_the_new_engine_answers_beside_the_old_before_the_old_is_replaced(tmp_path):
    code, calls = _switch(tmp_path)
    assert code == 0, calls
    built = _at(calls, "docker compose -f compose.server.yml build engine")
    standby = _at(calls, "docker compose -f compose.server.yml run -d --no-deps --name deploy-engine-standby")
    answered = _at(calls, "curl 8001 200")
    replaced = _at(
        calls, "docker compose -f compose.server.yml up -d --no-deps --no-build --force-recreate engine"
    )
    back = _at(calls, "curl 8000 200")
    gone = _at(calls, "docker stop --time 900 deploy-engine-standby")
    assert built < standby < answered < replaced < back < gone, calls
    assert "-p 127.0.0.1:8001:8000 -e ENGINE_STANDBY=1 engine" in calls[standby]
    assert not any("force-recreate caddy" in c for c in calls), "Caddy restarted with a file it already reads"


def test_a_new_engine_that_never_answers_leaves_the_old_one_serving(tmp_path):
    code, calls = _switch(tmp_path, down="8001")
    assert code == 1
    assert not any(" up " in c and c.endswith(" engine") for c in calls), "the old engine was replaced anyway"
    assert calls[-1] == "docker rm -f deploy-engine-standby", calls


def test_a_new_engine_on_8000_that_never_answers_leaves_the_standby_serving(tmp_path):
    code, calls = _switch(tmp_path, down="8000")
    assert code == 1
    assert not any("deploy-engine-standby" in c for c in calls[_at(calls, "curl 8001 200") :]), calls


def test_a_changed_caddyfile_is_read_by_a_new_caddy_before_anything_moves(tmp_path):
    code, calls = _switch(tmp_path, caddy_sees="{$ENGINE_HOST} {\n\treverse_proxy 127.0.0.1:8000\n}\n")
    assert code == 0, calls
    assert _at(calls, "docker compose -f compose.server.yml up -d --no-deps --force-recreate caddy") < _at(
        calls, "docker compose -f compose.server.yml run"
    )


def test_the_door_sends_each_request_to_whichever_engine_answers():
    """Caddy holds both places the engine can answer and asks each for /health; a request goes to the first that
    answered, and one that finds neither waits for one instead of failing at once. `caddy adapt --validate` on the
    caddy:2 image passed on this file (docs/notes/l8-deploy-without-downtime.md)."""
    caddy = (SWITCH.parent / "Caddyfile").read_text()
    proxy = re.search(r"reverse_proxy ([^{]+)\{(.*?)\}", caddy, re.S)
    assert proxy[1].split() == ["127.0.0.1:8000", "127.0.0.1:8001"]
    said = dict(line.split(None, 1) for line in proxy[2].strip().splitlines())
    assert said["lb_policy"] == "first" and said["health_uri"] == "/health"
    assert said["lb_try_duration"] == "30s", "a request finding no engine fails at once"
    ports = _load(SWITCH.parent / "compose.server.yml")["services"]["engine"]["ports"]
    assert ports == ["127.0.0.1:8000:8000"]


def test_a_deploy_switches_engines_instead_of_restarting_the_one():
    (job,) = _load(WORKFLOWS / "deploy-engine.yml")["jobs"].values()
    start = next(s for s in job["steps"] if s.get("name") == "start the engine")["run"]
    assert "bash switch.sh" in start and "up -d --build" not in start


def test_a_code_change_keeps_the_browser_and_the_readers_models():
    """Each deploy fetched Chromium (57 s) and the reader's models (37 s) again and wrote them out (52 s), because the
    whole engine was copied in above them. Only the reader's own file is now, and it reads nothing else of the engine."""
    runtime = (db.REPO_ROOT / "packages" / "engine" / "Dockerfile").read_text().split(" AS runtime", 1)[1]
    lines = [ln for ln in runtime.splitlines() if ln and not ln.startswith("#")]
    at = {
        key: next(i for i, ln in enumerate(lines) if key in ln)
        for key in ("playwright install", "digits._load()")
    }
    code = lines.index("COPY engine ./engine")
    assert at["playwright install"] < code and at["digits._load()"] < code, lines
    copied = [ln for ln in lines[: at["digits._load()"]] if ln.startswith("COPY engine")]
    assert copied == [
        "COPY engine/__init__.py engine/",
        "COPY engine/adapters/__init__.py engine/adapters/digits.py engine/adapters/",
    ]
    reader = (db.REPO_ROOT / "packages" / "engine" / "engine" / "adapters" / "digits.py").read_text()
    assert not re.search(r"^\s*(from|import) engine", reader, re.M), (
        "the reader needs more of the engine than is copied"
    )


def test_a_standby_leaves_the_serving_engines_runs_alone(monkeypatch):
    from fastapi.testclient import TestClient

    from engine.api import app as engine_app

    marked = []
    monkeypatch.setattr(engine_app.runs, "orphaned", lambda: marked.append(1))
    monkeypatch.setenv("ENGINE_STANDBY", "1")
    with TestClient(engine_app.app):
        pass
    assert marked == [], "the standby marked the serving engine's runs as dead"
    monkeypatch.delenv("ENGINE_STANDBY")
    with TestClient(engine_app.app):
        pass
    assert marked == [1], "an engine starting after one stopped no longer marks the runs that died with it"
