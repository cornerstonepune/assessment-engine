# cal-levels-to-review: Levels to review (a derived view and one page)

Goal `goals/cal_levels_to_review.yaml`. Nimish, 2026-10-26: when most of a grade or class is secure at a level, the level may be
too easy; the system only suggests; 80 percent; at least 8 children. BUILD-ORDER: no workflow gate moves. It sits beside the
inserted S5 slice (the curriculum page) as a ring-B view of the evidence, on Nimish's explicit word of 26 Oct.

## Verified

- **One rule for "secure".** The case that turned a child's answers into a state lived inside `rebuild_child_skill_state`. It is now
  `internal.graph_state_of`, called by that function and by the new view `child_level_state`.
  `test_the_shared_rule_gives_the_state_the_graph_always_gave` checks every combination of events, share, papers and repeated
  mistake against the old case; `test_graph.py` and `test_states_and_subject.py` still pass.
- **Secure at a level** = the state the rule gives on the confirmed answers to questions made for that level, where the school's
  `child_state` row says the state is `enough` and not `needs_work` (secure and ready to move up). A blank is an answer given and
  is not a success: that child counts as assessed and not as secure. Unconfirmed answers count for nothing (rule 4).
- **The numbers are rows**: `calibration.too_easy_share` 0.8, `calibration.min_children` 8, `calibration.review_again_children` 2
  (`supabase/seed/thresholds.json`, and the migration for live). Changing a row changes the verdict, with no deploy.
- **Append-only**: `calibration_review`, one row per "I've looked at this", with the counts it was looked at on; update and delete
  are refused. A looked-at suggestion comes back when the children assessed, or the children secure, move by 2.
- **The system never changes a level**: reading the view and recording a review leave `skill_level`, `skill_level_version` and `skill` byte-identical.
- **A person sees their own**: class rows for the classes in their scope; a grade's row only to someone whose scope holds every class of that grade.
- Page `/skill-sets/levels`, on `PageShell`, `DataTable`, `StatusChip`, `EmptyState`, `Count`, `FilterBar`; topic and skill fold.

Commands: `cd packages/engine && uv run pytest -q tests/test_calibration.py` (11 passed);
`cd apps/web && npx playwright test tests/u66-levels-to-review.spec.ts` (4 passed); `bin/check` (32 passed);
`bin/engine done cal_levels_to_review` (output in the PR).

## Handoff

- **Migration** `20261214090000_levels_to_review.sql` needs the rehearsal workflow (`rehearse-update-live.yml`) before merge: it
  replaces `rebuild_child_skill_state` (same results, case moved), adds a function, two views, a table and three threshold rows.
- **Not wired in** (other sessions own those files): the top menu and What needs doing. The line to add there: "Levels to review:
  N suggestions", from `levelsToReviewCount(scope)` in `apps/web/lib/queries-calibration.ts`; the page is `/skill-sets/levels`.
- **Data**: the self-seeded database has 614 levels, no child and no evidence, so every level reads "not assessed". Live was not reachable from this session.
- **Open for Nimish**: the 2-children rule for a suggestion to come back is my default, not his. And an Easy level that 80 percent
  of children are secure at is normal, not a defect: the page flags every level alike, as asked.
- **Selection bias**: a child is given Advance only after doing well, so the children assessed at Advance are already the strong ones, and "8 of 10 secure" is likely to be common there. Read the first live numbers with that in mind.
- "Too hard" (for example under 20 percent secure) is *not* free: the same counts give the share, but "not secure" includes children who are merely practising, which is normal at Hard. It would need its own definition (for example, share of children whose state needs work) and its own threshold row.
