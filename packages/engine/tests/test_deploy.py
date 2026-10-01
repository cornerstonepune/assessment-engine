"""What reaches live, and when (goals/p0-live-changes-wait-for-ci.yaml, goals/p0-papers-survive-a-deploy.yaml).

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
        after = [s.get("name") or s.get("uses") for s in steps[at + 1 :] if s.get("if") != GATED]
        assert after == [], f"{name} runs {after} even when a newer merge is on main"


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
