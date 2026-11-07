"""The fixed commands the `curriculum run` workflow runs on the server, from its one choice (RUN in the environment).

Nobody can run the K2 drafting commands on the box by hand, so a manual workflow does, and only these: no free text
reaches a shell. The run is a choice checked against RUNS below; the person who dispatched it is looked up in the
repository variable CURRICULUM_STAFF (a JSON map of GitHub login to staff email, kept outside git) and the email is
checked before it is quoted; the stage a command spends from, the money it may spend and the order of the stages are
the engine's (adapters/llm_budget.py, the config row llm.campaigns), so nothing here can raise a limit. A run that spends
nothing says so. Tested by packages/engine/tests/test_curriculum_run_command.py."""

import json
import os
import re
import shlex
import sys

EMAIL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._%+-]*@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}$")
BY = "{by}"  # where the dispatcher's email goes; the only substitution
CHECK_KEY = "import os; print(bool(os.getenv('ANTHROPIC_API_KEY')))"  # True or False: never the key
RUNS = {
    "key": {"spends": False, "commands": [["python", "-c", CHECK_KEY]]},
    "load_settings": {"spends": False, "commands": [["engine", "load", "--settings"]]},
    "forecast": {
        "spends": False,
        "commands": [
            ["engine", "curriculum", "draft", "--stage", "dev_eval", "--dev", "--dry-run"],
            ["engine", "curriculum", "draft", "--stage", "dev_eval", "--dev", "--use-kept", "--dry-run"],
            ["engine", "curriculum", "draft", "--stage", "draft", "--dry-run"],
            ["engine", "curriculum", "materials", "--stage", "draft", "--dry-run"],
            ["engine", "curriculum", "propose", "--version", "3", "--validate-version", "2", "--estimate"],
        ],
    },
    "map_probe": {
        "spends": True,
        "commands": [["engine", "curriculum", "map-probe", "--version", "3"]],
    },
    "map_dev": {
        "spends": True,
        "commands": [
            ["engine", "eval", "curriculum_map", "--dev", "--version", "3", "--validate-version", "2"]
        ],
    },
    "map_replay": {"spends": False, "commands": [["engine", "curriculum", "map-replay"]]},
    "map_replay_held_out": {
        "spends": False,
        "commands": [["engine", "curriculum", "map-replay", "--stage", "held_out"]],
    },
    "checkers": {"spends": False, "commands": [["engine", "curriculum", "checkers", "--stage", "dev_eval"]]},
    "draft_replay": {
        "spends": False,
        "commands": [["engine", "curriculum", "draft-replay", "--stage", "dev_eval"]],
    },
    "draft_record": {
        "spends": False,
        "commands": [
            ["engine", "curriculum", "draft-record", "--stage", "dev_eval", "--by", BY],
            ["engine", "curriculum", "draft-record", "--stage", "draft", "--by", BY],
        ],
    },
    "curriculum_apply": {
        "spends": False,
        "commands": [["engine", "curriculum", "apply", "--kind", "page_part", "--apply", "--by", BY]],
    },
    "draft_dev": {
        "spends": True,
        "commands": [["engine", "curriculum", "draft", "--stage", "dev_eval", "--dev", "--by", BY]],
    },
    "draft_dev_kept": {
        "spends": True,
        "commands": [
            ["engine", "curriculum", "draft", "--stage", "dev_eval", "--dev", "--use-kept", "--by", BY]
        ],
    },
    "map_held_out": {
        "spends": True,
        "commands": [["engine", "eval", "curriculum_map", "--version", "3", "--validate-version", "2"]],
    },
    "map_why": {"spends": False, "commands": [["engine", "curriculum", "map-why"]]},
    "map_propose": {
        "spends": True,
        "commands": [
            [
                "engine",
                "curriculum",
                "propose",
                "--stage",
                "draft",
                "--version",
                "3",
                "--validate-version",
                "2",
                "--apply",
                "--by",
                BY,
            ]
        ],
    },
    "draft_tranche": {
        "spends": True,
        "commands": [["engine", "curriculum", "draft", "--stage", "draft", "--tranche", "--by", BY]],
    },
    "draft_all": {
        "spends": True,
        "commands": [["engine", "curriculum", "draft", "--stage", "draft", "--by", BY]],
    },
    "materials_all": {
        "spends": True,
        "commands": [["engine", "curriculum", "materials", "--stage", "draft", "--by", BY]],
    },
    "review": {"spends": False, "commands": [["engine", "curriculum", "review"]]},
}


def person(actor: str, staff: str) -> str:
    """The dispatcher's staff email, from the variable; refuses, in words, anyone not on it or an email with shell in it."""
    try:
        mapping = json.loads(staff) if staff.strip() else {}
    except ValueError:
        mapping = {}
    email = mapping.get(actor) if isinstance(mapping, dict) else None
    if not isinstance(email, str) or not email:
        sys.exit(f"{actor or 'nobody'} is not on the list in the repository variable CURRICULUM_STAFF")
    if not EMAIL.fullmatch(email):
        sys.exit(f"the entry for {actor} in CURRICULUM_STAFF is not an email")
    return email


def email(run: str, actor: str, staff: str) -> str:
    """The dispatcher's staff email for a run whose commands carry it (every run that spends, and a free one that writes
    rows, which keep who ran them); nothing for the others. Refuses an unknown run."""
    if run not in RUNS:
        sys.exit(f"no run called {run!r}: one of {', '.join(RUNS)}")
    named = RUNS[run]["spends"] or any(BY in c for c in RUNS[run]["commands"])
    return person(actor, staff) if named else ""


def commands(run: str, actor: str, staff: str) -> list[str]:
    """The run's commands, each as one shell line with its words quoted."""
    who = email(run, actor, staff)
    return [shlex.join(who if word == BY else word for word in c) for c in RUNS[run]["commands"]]


if __name__ == "__main__":
    e = os.environ
    args = (e.get("RUN", ""), e.get("ACTOR", ""), e.get("STAFF", ""))
    if "--email" in sys.argv:  # for the workflow to mask it in the log before anything runs
        print(email(*args))
    else:
        print("\n".join(commands(*args)))
