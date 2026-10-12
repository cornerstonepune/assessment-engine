"""The rehearsal runs on a copy of live what `bin/update-live` runs on live, in its order
(`.github/workflows/rehearse-update-live.yml`).

They are two hand-kept lists of one sequence, and they drifted: AS2 put `bank rekey` first in update-live's step 5, and
its rehearsal on a copy of live passed without running it (CI on 2cd814c)."""

import os
import re
import subprocess

import yaml

from engine.core import db

ROOT = db.REPO_ROOT
# an engine command and its words, up to its first argument: `bank levels --apply`, `legacy paper`, `live data`
COMMAND = re.compile(r'(?:"\$E"|bin/engine) ((?:[a-z][a-z-]*|--apply)(?: (?:[a-z][a-z-]*|--apply))*)')
# read only, and not rehearsed: what waits on a person, printed on live and never failed on (`|| true`)
NOT_REHEARSED = {"audit"}


def _commands(text):
    return [
        m.group(1)
        for line in text.splitlines()
        if not line.lstrip().startswith("#")
        for m in COMMAND.finditer(line)
    ]


def test_the_rehearsal_runs_what_update_live_runs_in_its_order():
    live = [c for c in _commands((ROOT / "bin/update-live").read_text()) if c not in NOT_REHEARSED]
    workflow = yaml.safe_load((ROOT / ".github/workflows/rehearse-update-live.yml").read_text())
    runs = "\n".join(s.get("run", "") for job in workflow["jobs"].values() for s in job["steps"])
    rehearsed = _commands(runs)
    assert "bank rekey" in live and len(live) >= 12, live  # the reading itself, held to what update-live says
    left = iter(rehearsed)
    missing = [c for c in live if c not in left]  # a subsequence: every one, in update-live's order
    assert not missing, f"update-live runs {missing} where its rehearsal does not: {rehearsed}"


def test_going_live_keeps_the_servers_own_settings(tmp_path):
    """Found 2026-10-12: every `bin/update-live` runs `deploy/go-live.sh`, which swapped the server's folder for the new
    code and wrote its .env afresh from the Mac's three settings, so Jev's key, kept on the server alone, went with every
    update and Jev answered nothing on live. The swap carries the server's .env across, as `deploy-engine.yml` does, and
    the Mac's settings are written over it, every other line kept."""
    text = (ROOT / "deploy/go-live.sh").read_text()
    swap = next(ln for ln in text.splitlines() if "mv ~/assessment-engine.new ~/assessment-engine" in ln)
    assert "cp ~/assessment-engine/.env ~/assessment-engine.new/.env" in swap.split("rm -rf")[0], swap
    write = re.search(r'"\$\{SSH\[@\]\}" "(umask 077[^"]*)" < "\$WORK/env"', text)
    assert write, "go-live writes the settings in one command over ssh, the Mac's settings on its input"
    (tmp_path / "assessment-engine").mkdir()
    (tmp_path / "assessment-engine" / ".env").write_text("DATABASE_URL=old\nTYPESAFE_API_KEY=kept\n")
    subprocess.run(
        ["bash", "-c", write[1].replace("$KEYS", "DATABASE_URL|ENGINE_KEY")],
        input="DATABASE_URL=new\nENGINE_KEY=k\n",
        text=True,
        env={"HOME": str(tmp_path), "PATH": os.environ["PATH"]},
        check=True,
    )
    lines = (tmp_path / "assessment-engine" / ".env").read_text().splitlines()
    assert sorted(lines) == ["DATABASE_URL=new", "ENGINE_KEY=k", "TYPESAFE_API_KEY=kept"]
