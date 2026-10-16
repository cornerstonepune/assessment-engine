---
name: athena-ship
description: Use when a scoped change is built and verified (athena finish succeeded). Commits, pushes a feature branch, opens a pull request that closes its GitHub issue on merge, comments on the issue and records lessons.
---

# athena-ship: hand Nimish something he can merge

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
7. **Report** to Nimish in at most eight lines, as `.claude/athena/CLAUDE.md` describes.
