"""The rehearsal runs on a copy of live what `bin/update-live` runs on live, in its order
(`.github/workflows/rehearse-update-live.yml`).

They are two hand-kept lists of one sequence, and they drifted: AS2 put `bank rekey` first in update-live's step 5, and
its rehearsal on a copy of live passed without running it (CI on 2cd814c)."""

import re

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
