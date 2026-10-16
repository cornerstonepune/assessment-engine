---
name: athena-learn
description: Use at the end of every shipped or blocked change, and in the monthly harness review. Records what this repo taught the agent so the next session starts smarter; prunes stale lessons.
---

# athena-learn: the repo teaches the next agent

Lessons live in `docs/athena/learnings.md`, newest last. Create the file if it is missing, with the heading `# What this repo has taught us`. The last 15 lessons load into every session.

## After a change
Add at most three lessons, and only ones that would change what the next agent does in **this** repo. For example:
- a command that works;
- a trap you fell into;
- a convention the code follows;
- a proof pattern that suits this codebase.

No generic advice, nothing already in `CLAUDE.md`, no secrets. Use this format:

`- YYYY-MM-DD [<ID>] <lesson in one line> (evidence: <file, command or error>)`

If the same lesson is already there, don't add it again. Instead, if it has now come up three times, say in the pull request body: "Suggest promoting to CLAUDE.md: <lesson>".

## Monthly review (the harness-review routine)
- Delete lessons that are wrong or describe code that no longer exists.
- Merge duplicates.
- Propose promotions of repeated lessons into the repo's `CLAUDE.md`, as one pull request titled `athena: monthly lessons review`.
