---
name: athena-scope
description: Use when Nimish gives a GitHub issue (a number, a link or a spec ID like ATL-9), a scope file or a rough idea to build. Drafts the scope if needed, copies a locked scope into specs/<ID>/, has a separate agent write failing acceptance proofs, and locks them. Run before athena-build.
---

# athena-scope: lock what "done" means before any code

Announce: "Locking the scope and writing the proofs for <ID>."

## A. Nimish has only a rough idea
Draft the scope for him in plain English: **What**, **Done when** and **Out of scope**.
- *Done when* must be numbered outcomes a person or a test can observe. For example, "an exported CSV has one row per farmer with columns name, village, acreage". Avoid vague items like "export works well".
- Give it the next ID: `python3 .claude/athena/bin/athena next-id`.
- Create a GitHub issue in this repository titled `<ID>: <short title>`, with the body in the Scope form's layout (`### What`, `### Done when`, `### Out of scope`) and **without** the `scope-locked` label:
  `gh api repos/{owner}/{repo}/issues -X POST -f title="<ID>: <title>" -F body=@<file>`.
  Use `gh api` (REST), not `gh issue`; some sessions block GitHub's GraphQL. If `gh` is not signed in, show Nimish the draft instead.
- Also run `athena new <ID>` and copy the draft into `specs/<ID>/spec.md`, so the draft is in the repository too.
- Stop there. He edits the issue and adds the label when he agrees. Never add `scope-locked` yourself.

## B. A locked scope exists
1. **Fetch it.**
   - For a GitHub issue: `gh api repos/{owner}/{repo}/issues/<number>`. Given a spec ID instead, find the open issue whose title starts with `<ID>:` with `gh api "repos/{owner}/{repo}/issues?state=open&per_page=100"`.
   - The issue must carry the label `scope-locked`. If it doesn't, stop and say so.
   - Its title gives the ID. If the title still reads `<ID>`, take `athena next-id` and rename the issue (`-X PATCH -f title=...`).
   - For a scope file or text pasted in this session, Nimish must have said it is locked. Otherwise stop and say so.
2. **Check it can be proven.** Every *Done when* line must be observable.
   - If any line is vague, contradictory or missing, don't invent criteria.
   - Post the specific questions as a comment on the issue (`gh api repos/{owner}/{repo}/issues/<number>/comments -X POST -f body=...`), or ask Nimish directly in an interactive session, then stop.
3. **Branch.** If you are on `main` or `master`, `git checkout -b <id-lowercase>-<short-slug>`.
4. **Create the spec.**
   - Run `python3 .claude/athena/bin/athena new <ID> --title "<title>" --source "<issue url or file>"`. If the spec already exists as a draft, keep it and overwrite only its scope text.
   - Fill `specs/<ID>/spec.md` with *What*, *Done when* and *Out of scope*, copied **verbatim**. Keep the numbering. Don't paraphrase, merge or add items.
5. **Proofs, by a different agent.**
   - Dispatch the `athena-proof-writer` agent with the path `specs/<ID>/spec.md`.
   - It writes `checks.sh` and `proofs/` and returns a table: criterion → check → current result.
   - You must not write the proofs yourself.
6. **Review the proofs.**
   - There must be exactly one `check` per *Done when* line, with the same number.
   - Each must exercise real behaviour, not grep the source for a string, unless the criterion is about text.
   - Each must fail now for the right reason.
   - Send it back to the agent once if not. If a criterion is unprovable, go back to step 2.
7. **Lock.** Run `python3 .claude/athena/bin/athena lock <ID>`.
   - It refuses if the proofs don't run, or if they all already pass.
   - Then commit `specs/<ID>/` with message `<ID>: lock scope and proofs`.
8. **Tell Nimish**, in plain words, how we will know it's done: one line per criterion. Then continue with `athena-build` unless he asked only for scoping.
