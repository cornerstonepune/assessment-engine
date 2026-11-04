"""The fixed commands the `timetable run` workflow runs on the server, from its one choice (RUN in the environment).

The K2 timetable reaches the live database by a logged command on the box, not by SQL pasted through a connector. Two
runs only: `dry` loads the committed exports into a transaction it rolls back (prints counts, writes nothing) and
`apply` writes them, twice, so the log shows the second adding nothing. The files are the ones committed in
supabase/seed/k2_tabs_2026_11_04/ (the box mounts supabase/seed at /app/supabase/seed); no free text reaches a shell.
The person who dispatches an apply is looked up in the repository variable CURRICULUM_STAFF, as for the curriculum run,
by that script's own check. Tested by packages/engine/tests/test_timetable_run_command.py."""

import importlib.util
import os
import shlex
import sys
from pathlib import Path

_curriculum = importlib.util.spec_from_file_location(
    "curriculum_command", Path(__file__).resolve().parents[1] / "curriculum" / "command.py"
)
people = importlib.util.module_from_spec(_curriculum)
_curriculum.loader.exec_module(people)

TABS = "/app/supabase/seed/k2_tabs_2026_11_04"
LOAD = [
    "engine", "timetable", "load",
    "--frame", f"{TABS}/frame.csv", "--spans", f"{TABS}/frame_spans.json",
    "--planner", f"{TABS}/planner.csv", "--calendar", f"{TABS}/calendar.csv",
    "--section", "A", "--grade", "K2",
    "--undecided", "2026-12-07=graph-tab-and-calendar-disagree-on-the-fortnight-10-11-boundary",
]  # fmt: skip
RUNS = {
    "dry": {"writes": False, "commands": [LOAD]},
    "apply": {"writes": True, "commands": [[*LOAD, "--apply"], [*LOAD, "--apply"]]},
}


def commands(run: str, actor: str, staff: str) -> list[str]:
    """The run's commands, each as one shell line with its words quoted; refuses an unknown run, and an apply for anyone
    not on the list."""
    if run not in RUNS:
        sys.exit(f"no run called {run!r}: one of {', '.join(RUNS)}")
    if RUNS[run]["writes"]:
        people.person(actor, staff)
    return [shlex.join(c) for c in RUNS[run]["commands"]]


if __name__ == "__main__":
    e = os.environ
    print("\n".join(commands(e.get("RUN", ""), e.get("ACTOR", ""), e.get("STAFF", ""))))
