"""The `engine eval` command the engine-eval workflow runs on the server, from the workflow's inputs (PURPOSE, VERSION,
REVIEW, JEV in the environment). Each purpose is passed only the options it uses, and a version must be one the seed
holds (supabase/seed/prompts.json), so a new version can be scored the day it is seeded. Tested by
packages/engine/tests/test_eval_command.py."""

import json
import os
import pathlib
import shlex
import sys

SEED = pathlib.Path(__file__).resolve().parents[2] / "supabase" / "seed" / "prompts.json"
PURPOSES = (
    "parent_report",
    "parent_review",
    "mistake_guess",
    "story_shape",
    "week_skills",
    "english_generate",
)
# the purpose that takes each extra option, and the prompt whose version it names (None: any whole number)
EXTRA = {
    "review": ("parent_report", "--review-version", "parent_review"),
    "jev": ("parent_review", "--jev-version", None),
}


def _versions(purpose: str) -> set[str]:
    return {str(r["version"]) for r in json.loads(SEED.read_text())["prompts"] if r["purpose"] == purpose}


def _number(name: str, value: str) -> str:
    if not value.isdigit():
        sys.exit(f"{name} must be a whole number, not {value!r}")
    return value


def command(purpose: str, version: str, review: str, jev: str) -> list[str]:
    """The command's words; refuses, in words, a purpose or version the seed does not hold or an option not its own."""
    if purpose not in PURPOSES:
        sys.exit(f"no prompt {purpose!r} is scored here: one of {', '.join(PURPOSES)}")
    out = ["engine", "eval", purpose]
    if version.strip():
        if _number("version", version.strip()) not in _versions(purpose):
            sys.exit(f"{purpose} has no version {version} in supabase/seed/prompts.json")
        out += ["--version", version.strip()]
    for name, value in (("review", review.strip()), ("jev", jev.strip())):
        owner, option, of = EXTRA[name]
        if not value:
            continue
        if purpose != owner:
            sys.exit(f"{name}_version is used by only {owner}, not {purpose}: leave it empty")
        if of and _number(f"{name}_version", value) not in _versions(of):
            sys.exit(f"there is no {of} version {value} in supabase/seed/prompts.json")
        out += [option, _number(f"{name}_version", value)]
    return out


if __name__ == "__main__":
    e = os.environ
    print(shlex.join(command(e["PURPOSE"], e.get("VERSION", ""), e.get("REVIEW", ""), e.get("JEV", ""))))
