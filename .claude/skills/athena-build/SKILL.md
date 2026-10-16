---
name: athena-build
description: Use to build a scoped change end to end, for example "build UNC-12". Runs scope first if the spec isn't locked, then plans, builds test-first until every locked proof passes, verifies independently and ships a pull request. Works unattended in routines.
---

# athena-build: from locked scope to a pull request Nimish can merge

Announce: "Building <ID> under the Athena loop."

1. **Locked scope?** If `specs/<ID>/LOCK` does not exist, run the `athena-scope` skill first.
2. **Branch.** If you are on `main` or `master`, `git checkout -b <id-lowercase>-<short-slug>`.
3. **Start.** Run `python3 .claude/athena/bin/athena start <ID>`. From now on the stop gate holds the session until the proofs pass.
4. **Understand.** Read:
   - the repo's `CLAUDE.md` and `specs/<ID>/spec.md`;
   - the proofs, which are read-only;
   - `docs/athena/learnings.md`;
   - the code the change touches.
   Check whether a well-maintained open-source package already solves a generic part (adopt before you build).
5. **Plan.** Use the `writing-plans` skill. Save the plan to `specs/<ID>/plan.md`. Each task names the *Done when* numbers it serves. Anything that serves no number is out of scope: drop it.
6. **Build.**
   - Use `subagent-driven-development` for multi-task plans, or `executing-plans` for small ones.
   - Every task follows `test-driven-development`, with unit tests in the repo's normal test folders.
   - After each task, run `python3 .claude/athena/bin/athena done <ID>`.
   - Use `systematic-debugging` when a failure isn't obvious.
   - Fix product code only; the proofs are locked.
7. **No regressions.** When the proofs pass, run the repo's full test suite and linters if they exist, and fix what you broke.
8. **Stop rule.** Run `python3 .claude/athena/bin/athena block <ID> "<plain-English reason>"` and stop when:
   - the same failure repeats three times;
   - a proof looks wrong;
   - the scope is ambiguous; or
   - you need access, credentials or a decision.
   In a routine or unattended run, never ask a question: block instead.
9. **Verify.** Run the `athena-verify` skill.
10. **Ship.** Run the `athena-ship` skill.

Never claim progress without fresh `athena done` output from this session.
