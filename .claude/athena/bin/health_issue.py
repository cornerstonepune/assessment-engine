#!/usr/bin/env python3
"""Nightly: run `athena health` (the scorecard is in the Actions log), then keep one GitHub issue "Athena health: <date>" in step.

No AI model is involved. Failures open or update the issue; a clean run closes it. --dry-run prints the issue
text instead of calling GitHub. Standard library plus the `gh` command that GitHub Actions already has.
"""
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

BIN = Path(__file__).resolve().parent
LABEL = "athena-health"


def athena(cmd):
    r = subprocess.run([sys.executable, str(BIN / "athena"), cmd], capture_output=True, text=True)
    return r.returncode, r.stdout.strip()


def gh(*args, body=None):
    cmd = ["gh", "api", *args]
    if body is not None:
        cmd += ["--input", "-"]
    r = subprocess.run(cmd, input=json.dumps(body) if body is not None else None, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"gh api failed: {r.stderr.strip()}")
    return json.loads(r.stdout or "null")


def main(argv):
    dry = "--dry-run" in argv
    today = datetime.now(timezone.utc).date().isoformat()
    code, health = athena("health")
    if code not in (0, 1) or (code == 1 and "FAIL" not in health):  # a crash must never read as a clean night
        sys.exit(f"athena health crashed (exit {code}): {health[-300:]}")
    fails = [l for l in health.splitlines() if l.startswith("FAIL")]
    if not fails:
        text = "No failures: close the open 'Athena health' issue."
    else:
        text = f"Athena health: {today}\n\n" + "\n".join("- " + l[5:] for l in fails)
    if dry:
        print(text)
        return 0
    repo = os.environ["GITHUB_REPOSITORY"]
    open_ = gh(f"repos/{repo}/issues?state=open&labels={LABEL}&per_page=1")
    if fails:
        body = {"title": f"Athena health: {today}", "body": text}
        if open_:
            gh(f"repos/{repo}/issues/{open_[0]['number']}", "-X", "PATCH", body=body)
        else:
            gh(f"repos/{repo}/issues", "-X", "POST", body={**body, "labels": [LABEL]})
    elif open_:
        gh(f"repos/{repo}/issues/{open_[0]['number']}", "-X", "PATCH", body={"state": "closed"})
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
