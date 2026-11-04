# M1-15 — skill links: reason, who confirmed it, and nothing reads an unconfirmed one

W3, gate N10. Goal `goals/m1-15-skill-links.yaml`, decision `docs/adr/0099-…`. Migration `20270103090000_skill_links.sql`.

## What changed
- `skill_link` (new): links between the 244 broad skills (`registry_skill`) with strength, reason, source, status, confirmed_by,
  confirmed_at. Strength and status are rows (`link_strength`, `link_status`; `link_status.confirmed` marks the state a reader may use).
- `skill_prerequisite` (282 rows, micro-steps) gains the same columns. All 282 are `proposed`, source `seed rule`, strength `soft`
  (167 maths with the grade-rule reason, 115 English with "drafted with the English foundation"). None is confirmed.
- Views `skill_link_confirmed`, `skill_prerequisite_confirmed` show confirmed links only. `skill_link_audit` and
  `skill_prerequisite_audit` show every row; only `checks/links.py` and `checks/scenarios_links.py` may read them (a test holds it).
- A ring among `skill_link` rows is refused (the pattern of `internal.skill_prerequisite_no_circle`), proposed rows counted.
- `engine skill-links load <csv>` (proposals, idempotent, all-or-nothing, names the bad line) and
  `engine skill-links confirm <id> --by <email>` (existing, active staff only; the first confirmation stands).
- Seeders (`core/topics.py`, `core/english.py`) insert `proposed`, source `seed rule`: neither seed was checked link by link.

## Who read `skill_prerequisite` before (found by grep over engine, apps/web, SQL)
Only `checks/links.py` (a count and a ring walk for `engine links check`), the two seeders and the loader's row counts. No screen, no
paper, no graph function. `apps/web/lib/queries-report.ts:118` names it in a comment only. So no live feature depends on the raw
table; `links check` now reads `skill_prerequisite_audit`, which returns the same rows (282 here).

## Not verified / limits
- Not run on live or a copy of live. `rehearse-update-live` (states_may_change off) is for the orchestrator after the push.
- The website role still has SELECT on the raw tables (the repo's default grant); "nothing reads an unconfirmed link" is held by
  the scan tests, not by database privileges. Making the views owner-run would break the repo's `security_invoker` habit and I could
  not verify the owner's RLS bypass on live.
- The educator's pairs have not arrived; the scenario uses a three-pair test list (`goals/fixtures/m1-15-test-pairs.csv`).
- "refusing a self-confirmation of nothing" read as: refuse an unknown id, an unknown or inactive staff email, a blank `--by`.
- Strength of the 282 set to `soft` is my choice (a grade rule cannot say "needed"); nothing reads it.

## Handoff
Next: orchestrator confirms main has M1-10's migration, then one push (draft PR), then the rehearsal on a copy of live. Then the
educator's list: `bin/engine skill-links load <file>`, a person confirms each by id.

## Verified
(filled in below from the last runs)
