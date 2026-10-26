# perf-slow-site — Check answers took seconds a click (fault fix, no gate moved)

Nimish, 2026-10-26: "Once I click what the child has written, it literally takes a few seconds to go to the next one. This
wasn't the case previously." — "slow on all clicks". Goal: `goals/perf-slow-site.yaml`.

## Verified

All timings are **local** (this container's Postgres 16 and a production build of the site, 80 answers waiting over 12
papers, each a two-page 12-megapixel photo PDF). Live was not reachable and is not measured. Statements are counted in the
database's own log (`log_statement=all`), site / engine.

Command: `cd apps/web && npx playwright test tests/p6-check-is-quick.spec.ts` (the spec seeds the 12 papers itself).

| Request | Before | After |
|---|---|---|
| open `/capture/check` | 9082 ms · 21 + 8 statements | 476 ms · 21 + 10 |
| one click of "Yes, the child wrote 84" | 9720 ms · 24 + 19 | 224 ms · 24 + 21 |
| open `/today` (What needs doing) | 411 ms · 24 | 487 ms · 24 |
| open `/school` (Children) | 163 ms · 20 | 159 ms · 20 |
| open `/papers` (Assessments) | 470 ms · 29 | 473 ms · 29 |
| open `/growth` (Results) | 153 ms · 23 | 163 ms · 23 |
| open `/` (Skills) | 470 ms · 26 | 435 ms · 26 |

The other five pages were never slow here: this is not the menu counts, the teacher scope, or a missing index.

**Cause:** each card asked the engine for `GET /capture/{id}/proof` (whose paper it is, #314), and that drew the photograph of
every page of every copy cut from the same scan file, and decoded each one for a fingerprint, on every card (about 0.5 s a
page, 8.7 s for the first card measured by hand: `curl` of that route alone). The site, the keys and the crop took 10–20 ms each.
Evidence: bisect by route (proof 8.7 s, keys 0.015 s, crop 0.022 s); `edbf455` (#314) added it.

**Fix:** a page's fingerprint and printed code are facts of a file that never changes: told once per page into
`capture_page` (migration `20261213090000`, append-only, RLS by `apply_conventions`), at reading time
(`whose_paper.record`) and, for files read before, on the first card and kept. A card reads rows.

Proofs: `packages/engine/tests/test_whose_paper.py` (the card never draws a photograph again); the budget spec above.

## Handoff

- Migration: **run the rehearsal workflow (`rehearse-update-live.yml`) on this branch before merge.**
- Not measured on live: network and region (bom1 ↔ Supabase Mumbai), the engine's disk. Files read before this change are
  told on their first card (one slow card per file, once), then quick.
- Seen, not fixed (not this cause): `tests/test_profiles.py::test_kind_trust_is_the_last_fifty_checks…` fails on unchanged main
  on this fresh local database (a `legacy_bare` kind); it passes in CI's own run.
