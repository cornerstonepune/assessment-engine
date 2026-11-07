---
name: athena-ship
description: Use when a scoped change is built and verified (athena finish succeeded). Commits, pushes a feature branch, opens a pull request that closes its GitHub issue on merge, comments on the issue and records lessons.
---

# athena-ship: merge it yourself once every gate holds

1. **Check readiness.** `specs/<ID>/status.json` must say `built`, and `specs/<ID>/VERIFY.md` must exist. If not, go back to `athena-verify`.
2. **Commit.** Run `git add -A` and `git commit -m "<ID>: <title>"`. Never commit secrets, `.env` files or client data.
3. **Push** the feature branch: `git push -u origin HEAD`. Never push to main. In a cloud session, push to the branch the session allows.
4. **Open the pull request.** Use `gh api repos/{owner}/{repo}/pulls -X POST` (REST; `gh pr create` needs GraphQL, which some sessions block); otherwise use the GitHub tools available; otherwise give the compare URL. The title is `<ID>: <title>`. The body follows this layout:

   ```
   ## For Nimish
   <3-5 plain-English lines: what changes for a user, what to try, anything risky>

   ## How we know it's done
   | # | Done when | Proof | Result |
   |---|---|---|---|
   <one row per criterion, from athena done>

   ## Independent check
   <verdict and any notes from VERIFY.md>

   ## Choices made
   <adopt-before-build decisions, new dependencies and why; "none" if none>

   Closes #<issue number>   (the scope issue: the Source line of spec.md, or the open issue whose title starts with `<ID>:`; leave this line out if the scope came from a file)
   ```

5. **Comment on the issue** with the PR link and the "For Nimish" lines (`gh api repos/{owner}/{repo}/issues/<number>/comments -X POST`). Don't close it: merging closes it.
6. **Record lessons.** Run the `athena-learn` skill.
7. **Merge** the pull request without waiting for Nimish, when all of these hold on its latest commit: every CI check is green, `specs/<ID>/VERIFY.md` in the pull request says PASS from the independent verifier (tier 2 and 3), no red-circle review finding is open, and the pull request is mergeable. If any one fails, do not merge: fix it, or report what is stopping it. Merge with `gh api repos/{owner}/{repo}/pulls/<number>/merge -X PUT -f merge_method=squash`, or turn on auto-merge or use the merge queue where the repository already has them (turning them on needs Nimish's yes for that repository). There are no exceptions: migrations, deploy paths, money and client data merge under these same conditions.
   - Several open pull requests in one repository merge one at a time. After each merge, bring the next one up to date with main and wait until its checks are green again before it merges. A conflict stops only that pull request and is reported; the others continue.
   - After each merge, watch the checks on main. If main turns red, open a revert pull request in the same session and report it to Nimish.
8. **Report** to Nimish in at most eight lines, as `.claude/athena/CLAUDE.md` describes. List each pull request you merged, one line each, with the checks that were green.
