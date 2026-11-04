# m1-11h: the drafted-pages sheet as a staff-only download, never a log

## Verified
- `cd packages/engine && uv run pytest -q tests/test_k2_gold.py tests/api/test_gold_sheet_route.py tests/test_curriculum_run_command.py tests/test_contract.py` → passed (fresh database, local).
- `cd apps/web && npx next typegen && npx tsc --noEmit && npx eslint --max-warnings 0 app/api/gold-sheet tests/gate.spec.ts` → clean.
- `bin/check` → see the PR.
- Not verified: opening `/api/gold-sheet` signed in on the live site (this session has no sign-in there); the unsigned 401 is a browser test (`gate.spec.ts`), run by CI.

## Why
`gold_sheet` ran on 2026-11-04 (run 41913769810) and printed nothing. Two causes, both found:
1. The sheet read pages whose drafts had been applied (`activity_part_source`); the 99 drafted so far are in the ledger,
   recorded and unapplied. It now reads the ledger's page proposals (not rejected, not reverted).
2. Its only way out was a run's log. This repository and its Actions logs are public and the sheet holds the school's
   lesson text. The run choice is gone from the workflow and the allowlist, and the command writes only to `--out FILE`
   and prints a count.

## What it is now
- Engine: `GET /curriculum/gold-sheet.csv?by=<email>&pages=N` (engine key + a sign-in on the staff list, else 401/403;
  `attachment`, `no-store`; 1..100 pages). The sheet itself is unchanged: school text beside the draft, two empty columns,
  nothing the machine said.
- Site: `/api/gold-sheet` (signed-in staff only: `proxy.ts` and the handler both answer 401) streams the engine's CSV as a
  download. No page renders it and nothing writes it to disk.

## Handoff
- After deploy: signed in, open `/api/gold-sheet`; the browser saves `k2-drafts-to-mark.csv`. It is never committed.
