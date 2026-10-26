---
name: athena-verify
description: Use after a scoped change's proofs pass and before shipping. A different model, read-only, checks the change against the locked scope for unmet criteria, unasked work and missing promises.
---

# athena-verify: an independent second opinion

1. Run `python3 .claude/athena/bin/athena done <ID>` and keep the output.
2. Get the base branch, usually `main`, and run `git diff --stat <base>...HEAD -- . ':!specs'`.
3. **Dispatch the `athena-verifier` agent.** Give it the spec path, the base branch and the `athena done` output. Don't give it your own opinion of the work.
   If the change alters an existing harness component (plugin, skill, hook or agent), also give it the component's `athena scorecard` row and tell it to answer FAIL unless a proof shows that component fired in a recorded session; for a gate or schedule, its CI or routine run record is that proof. A newly added component cannot have fired yet: verify it by its proofs and note that its first fire is pending (`athena health` flags it if it never fires).
4. Save its answer verbatim to `specs/<ID>/VERIFY.md`.
5. **If the verdict is FAIL:**
   - Remove unasked work, or add what is missing, then run steps 1–4 once more.
   - If it still fails, or the disagreement is about what the scope means, run `athena block <ID> "<reason>"` and stop.
6. **If the verdict is PASS,** run `python3 .claude/athena/bin/athena finish <ID>`.
