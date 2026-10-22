"""What reaches live, and when (goals/p0-live-changes-wait-for-ci.yaml, goals/p0-papers-survive-a-deploy.yaml,
goals/l4-the-website-waits-for-the-database.yaml, goals/l14-migrations-wait-for-locks.yaml).

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
    assert push["run"] == "bin/push-migrations", "the status is not set after the migration"
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


PUSH = db.REPO_ROOT / "bin" / "push-migrations"
IN_BAND = "set lock_timeout = '3s'; set statement_timeout = '10min';"
SQL = "create view {} as select 1;\n"


def _push_step() -> dict:
    (job,) = _load(WORKFLOWS / "migrate.yml")["jobs"].values()
    return next(s for s in job["steps"] if s.get("name") == "apply what live is missing")


def _settings() -> str:
    """The lines bin/push-migrations puts first in every migration, read from the script itself."""
    return re.search(r"<<'SQL'.*?\n(.*?)\nSQL\n", PUSH.read_text(), re.S)[1]


def _checkout(tmp_path, answers):
    """A checkout holding bin/push-migrations, bin/update-live and two migrations, with a `supabase` that answers each
    try from `answers` ("ok", "lock" for SQLSTATE 55P03, anything else another failure), writes down the first line of
    the migrations it was handed and keeps a copy of them, and a sleep that only writes down that it was called →
    (the checkout, the environment to run it in)."""
    import os
    import shutil

    bin_ = tmp_path / "fakes"
    bin_.mkdir()
    fakes = {
        "sleep": 'echo "sleep $1" >> "$LOG"\n',
        "supabase": 'while [ $# -gt 0 ]; do [ "$1" = --workdir ] && w=$2; shift; done\n'
        'echo "push $(head -qn1 "$w"/supabase/migrations/*.sql | sort -u)" >> "$LOG"\n'
        'rm -rf "$GOT"; cp -r "$w/supabase/migrations" "$GOT"\n'
        'a=$(head -1 "$ANSWERS"); sed -i 1d "$ANSWERS"\n'
        'case "$a" in ok) echo "Finished supabase db push." ;;\n'
        '  lock) echo "ERROR: canceling statement due to lock timeout (SQLSTATE 55P03)"; exit 1 ;;\n'
        '  *) echo "ERROR: relation \\"x\\" does not exist (SQLSTATE 42P01)"; exit 1 ;; esac\n',
    }
    for name, body in fakes.items():
        (bin_ / name).write_text("#!/usr/bin/env bash\n" + body)
        (bin_ / name).chmod(0o755)
    (tmp_path / "calls").touch()
    (tmp_path / "answers").write_text("\n".join(answers) + "\n")
    checkout = tmp_path / "checkout"
    migrations = checkout / "supabase" / "migrations"
    migrations.mkdir(parents=True)
    shutil.copy(db.REPO_ROOT / "supabase" / "config.toml", checkout / "supabase")
    for name in ("20990101000000_a", "20990102000000_b"):
        (migrations / f"{name}.sql").write_text(SQL.format(name[-1]))
    (checkout / "bin").mkdir()
    for name in ("push-migrations", "update-live"):
        shutil.copy(db.REPO_ROOT / "bin" / name, checkout / "bin")
    env = {
        **{k: v for k, v in os.environ.items() if k != "PGOPTIONS"},
        "PATH": f"{bin_}:{os.environ['PATH']}",
        "LOG": str(tmp_path / "calls"),
        "ANSWERS": str(tmp_path / "answers"),
        "GOT": str(tmp_path / "pushed"),
    }
    return checkout, env


def _push(tmp_path, answers):
    """migrate live's push step run as the runner runs it (`bash -e`, in the checkout) → (exit code, every call in
    order)."""
    import subprocess

    checkout, env = _checkout(tmp_path, answers)
    step = _push_step()
    env = {**env, **step["env"], "LIVE": "postgresql://nobody@127.0.0.1:1/none"}
    done = subprocess.run(
        ["bash", "-e", "-c", step["run"]], env=env, cwd=checkout, capture_output=True, text=True
    )
    return done.returncode, (tmp_path / "calls").read_text().splitlines()


def _pushed() -> str:
    return "push " + _settings()


def _in_band(tmp_path):
    """Each migration as it was pushed: the settings, then the migration as the checkout holds it, unchanged."""
    for migration in (tmp_path / "checkout" / "supabase" / "migrations").glob("*.sql"):
        assert migration.read_text() == SQL.format(migration.stem[-1]), (
            "the checkout's own migration was rewritten"
        )
        assert (
            tmp_path / "pushed" / migration.name
        ).read_text() == _settings() + "\n" + migration.read_text()


def test_a_migration_waits_briefly_for_a_lock_and_long_for_its_work():
    """2026-10-21 12:52 UTC: a view's replacement waited 121 s behind live's readers until live's 2-minute statement
    timeout cancelled it (SQLSTATE 57014), educators' queries on that view queued behind it all the while."""
    assert _settings().startswith(IN_BAND), (
        "a migration still waits on educators' locks, or dies at live's 2 minutes"
    )


def test_the_settings_travel_inside_each_migration_not_with_the_connection(tmp_path):
    """2026-10-22 02:01 and 02:09 UTC (run 39709016021, both attempts): live is reached through Supabase's pooler,
    which does not pass a connection's startup options on, so PGOPTIONS never reached live, and the check that read
    them back over a second connection failed and held the website with nothing to apply. The settings are now the
    first statements of every migration, inside the transaction the push runs it in, whatever the pooler does."""
    code, calls = _push(tmp_path, ["ok"])
    assert code == 0
    assert "PGOPTIONS" not in _push_step()["env"], "the settings still ride on the connection a pooler drops"
    assert calls == [_pushed()], f"{calls}: no push, or a check on a connection other than the migration's"
    _in_band(tmp_path)


def test_a_hand_update_of_live_pushes_the_same_settings(tmp_path):
    """2026-10-22 (L14c): bin/update-live, run by a person, still ran `supabase db push` itself, without the settings,
    so a hand update could queue educators' pages behind a lock as the 12:52 one did. It now runs the same step as
    migrate live, and leaves the checkout's migrations as main has them, for the next `git pull --ff-only`."""
    import subprocess

    checkout, env = _checkout(tmp_path, ["ok"])
    for fake, body in {"git": "", "uv": "", "bin/engine": 'echo "engine $1" >> "$LOG"'}.items():
        path = (tmp_path / "fakes" / fake) if "/" not in fake else (checkout / fake)
        path.write_text(f"#!/usr/bin/env bash\n{body}\n")
        path.chmod(0o755)
    python = checkout / "packages" / "engine" / ".venv" / "bin" / "python"
    python.parent.mkdir(parents=True)
    python.write_text("#!/usr/bin/env bash\n")
    python.chmod(0o755)
    (checkout / ".env").write_text("DATABASE_URL=postgresql://nobody@127.0.0.1:1/none\n")
    done = subprocess.run(
        [checkout / "bin" / "update-live", "--no-server"], env=env, capture_output=True, text=True
    )
    assert done.returncode == 0, done.stdout + done.stderr
    calls = (tmp_path / "calls").read_text().splitlines()
    assert calls[0] == _pushed(), (
        f"{calls[:2]}: the hand update pushed without the settings, or after the engine ran"
    )
    _in_band(tmp_path)


def test_every_path_to_live_pushes_through_one_step():
    """A second copy of the push is how bin/update-live was left without the settings: only bin/push-migrations runs
    `supabase db push`, and migrate live and bin/update-live each run it."""
    runs = [
        path.relative_to(db.REPO_ROOT).as_posix()
        for folder in ("bin", "deploy", ".github/workflows")
        for path in sorted((db.REPO_ROOT / folder).iterdir())
        if path.is_file()
        and any(
            "supabase db push" in line and not line.strip().startswith("#")
            for line in path.read_text().splitlines()
        )
    ]
    assert runs == ["bin/push-migrations", "bin/testdb"], (
        runs
    )  # bin/testdb pushes to the local copy, never to live
    assert _push_step()["run"] == "bin/push-migrations"
    assert 'LIVE="$LIVE" "$REPO/bin/push-migrations"' in (db.REPO_ROOT / "bin" / "update-live").read_text()


def test_the_cli_that_pushes_is_the_version_rehearsed():
    """The settings hold for a migration because the CLI runs its statements and its history row as one batch; that
    was rehearsed on supabase 2.121.0 (docs/notes/l14b-timeouts-in-band.md). `latest` would bring an unrehearsed CLI
    to live on whatever day it changed."""
    (job,) = _load(WORKFLOWS / "migrate.yml")["jobs"].values()
    (cli,) = [s for s in job["steps"] if s.get("uses", "").startswith("supabase/setup-cli")]
    assert cli["with"]["version"] == "2.121.0", (
        f"migrate live's CLI is {cli['with']['version']}, not the one rehearsed"
    )


def test_a_migration_whose_session_lacks_the_settings_stops_before_any_change():
    """The check runs inside the migration's own transaction, on the backend that runs it: with the settings it
    passes; without them it raises, so the migration's transaction rolls back before any change."""
    import psycopg
    import pytest

    settings = _settings()
    with db.connect() as conn:
        conn.execute(settings)
        took = "select current_setting('lock_timeout') as l, current_setting('statement_timeout') as s"
        assert conn.execute(took).fetchone() == {"l": "3s", "s": "10min"}
        conn.execute("reset all")
        with pytest.raises(psycopg.errors.RaiseException, match="did not take lock_timeout 3s"):
            conn.execute(settings.removeprefix(IN_BAND))


def test_a_migration_held_by_a_lock_tries_again_by_itself(tmp_path):
    code, calls = _push(tmp_path, ["lock", "lock", "ok"])
    assert code == 0
    assert [c for c in calls if c.startswith("push ")] == [_pushed()] * 3, calls
    assert calls.count("sleep 20") == 2, calls


def test_a_migration_that_fails_for_another_reason_stops_at_once(tmp_path):
    code, calls = _push(tmp_path, ["other", "ok"])
    assert code == 1
    assert [c for c in calls if c.startswith(("push", "sleep"))] == [_pushed()]


def test_a_migration_still_held_after_six_tries_fails(tmp_path):
    code, calls = _push(tmp_path, ["lock"] * 7)
    assert code == 1
    assert sum(c.startswith("push") for c in calls) == 6, calls


def test_the_model_key_reaches_the_server_from_the_repositorys_secret():
    """From 29 Sep the server's .env had no ANTHROPIC_API_KEY and every model call failed quietly for three weeks
    (PR #248). Each deploy now writes the repository's secret into .env, over ssh on stdin so no log or command line
    carries it, and a server still without it is a warning on the run (goals/k1-the-server-has-the-model-key.yaml)."""
    steps = _load(WORKFLOWS / "deploy-engine.yml")["jobs"]["deploy"]["steps"]
    names = [s.get("name", "") for s in steps]
    step = steps[names.index("the model key, from the repository's secret")]
    assert names.index("the model key, from the repository's secret") < names.index("start the engine")
    assert step["if"] == GATED
    assert step["env"]["ANTHROPIC_API_KEY"] == "${{ secrets.ANTHROPIC_API_KEY }}"
    script = step["run"]
    assert "printf '%s' \"$ANTHROPIC_API_KEY\" | $S" in script, "the key goes on stdin"
    assert 'echo "$ANTHROPIC_API_KEY' not in script and '$S "' not in script, "the key on a command line"
    assert 'grep -v "^ANTHROPIC_API_KEY="' in script, "an old key line is replaced, not doubled"
    assert "::warning::the server has no ANTHROPIC_API_KEY" in script
