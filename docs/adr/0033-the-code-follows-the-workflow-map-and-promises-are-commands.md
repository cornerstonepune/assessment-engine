# 0033 — The code follows the workflow map, and a promise is a command

Date: 2026-09-22
Status: accepted (Nimish, "Build these checks … Let's first go ahead and do the three steps")
Goal: goals/workflows-visible.yaml

## Context

The twelve steps agreed with the school (docs/sources/assessment-workflow-v1.md) and their four workflows
(ARCHITECTURE.md §6.1) existed only in prose. The engine was 40 modules in one folder, 14,755 lines, nine
files over the 400-line ceiling, one of them doing two jobs. Rules lived in CLAUDE.md, HANDOFF and memory,
and decayed in long sessions: ADR 0007's learning loop was designed on 2026-09-19 and found unbuilt on
2026-09-22, hidden behind a goal-file line (`correction_must_change_a_later_read: true`) that nothing ran.
Nimish: *"Despite putting all of this in the handoffs and Claude MDs, you keep on forgetting … Even if this
engine starts working, I can't go and say to the school with confidence, 'Let's start using this for other
subjects as well.'"*

## Decision

1. **One map, `workflows.json`**, names every step, what it takes and gives, who does it, whether it is built,
   whether it works for any subject (and what a new subject needs), the files, commands and screens that do
   it, the only connections one workflow makes to another, and the files over the ceiling.
2. **The code follows the map**: one folder per workflow (`w1_bank`, `w2_print`, `w3_read`) on `core`,
   `assess` and `adapters`; `checks`, `api` and `cli.py` are thin doors. `tests/test_layout.py` fails on a file
   on no step, an undeclared connection, a file past its ceiling, a step with no subject mark, or a command or
   screen that does not exist.
3. **The How it works page** draws the same file with each step's live number from the database.
4. **A promise is a command** (`engine promises`): a goal holds only its sentence, Nimish's words each with
   the test that proves it (`says`), scenarios, commands, and manual steps; a decision record from 0032 on
   names its goal.
5. **The checks run by themselves**: `bin/check` (layout, promises, lint; ~3 s, no database) runs before every
   commit (`.githooks/pre-commit`) and before Claude Code may end a turn (`.claude/settings.json`, Stop hook).
6. **Done is a report the machine writes** (`engine done <goal>`): each of his sentences with its test run now
   on the copy, what is still manual, what is not live yet.

## Rejected

- **The map as rows in the database** (rule 1's usual home for structure). The map describes code, so it
  lives with the code and is checked against it in CI; rows would need a load on every environment and could
  drift from the files they name.
- **A map only, the flat folder kept.** The layout Nimish asked to see would still be invisible in the code;
  a folder per workflow makes a wrong connection a visible import across folders, and the check refuses it.
- **Raising a ceiling when the move grew a file by a line.** Each growth was split along a real job instead
  (`bank.py` / `inventory.py`, `legacy.py` / `marking.py`, `cli.py` → `cli_bank.py`, `cli_week.py`).
- **More prose in CLAUDE.md or HANDOFF.** That is what decayed.
