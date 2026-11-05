# m0-03-today-speed — What needs doing was slower than its neighbours (fault fix, no gate moved)

Task M0-03. Goal: `goals/m0-03-today-speed.yaml`. Test (unchanged): `apps/web/tests/u65-what-needs-doing-walk.spec.ts`
"What needs doing opens in under a second, as the other pages do".

## Verified

**Cause.** Every page in the app group pays for the same list (the layout asks `tasksFor` for the menu's count; the page's
own call is the same cached reading). `/today` alone then did three more things in turn, after the list: `workScope`, then
`weekNote` (three queries, the note under the list). So `/today` took the list plus the note, where the others take the list.
The note's queries grow with the week's evidence (`evidence_event` has no index on `observed_at` alone, so one of them reads
the table; 29,000 rows: 37 ms alone on this machine), and they wait for a free connection while the list's queries hold them.

**Fix.** `apps/web/app/(app)/today/page.tsx`: the note is started as soon as the page knows the subject and the classes (both
need only `choices()` and `workScope`, not the list) and awaited where it is drawn. No query changed; no migration.

**Measured** (this machine, production build, local copy with 41 classes of 12 children, 160 read papers, 12,050 skill states,
28,920 evidence events, 2,400 taught-skill rows; `bin/testdb fresh` plus rows added for the measure; ms, median of 3, warm):

| | /today | /papers | /growth | / | /capture/check | /skill-sets/approve |
|---|---|---|---|---|---|---|
| before, run 1 | 1462 | 1167 | 1082 | 1304 | 1101 | 1211 |
| before, run 2 | 1363 | 1402 | 1079 | 1185 | 1198 | 1384 |
| after, run 1 | 1204 | 1317 | 1043 | 1263 | 1058 | 1159 |
| after, run 2 | 1041 | 1232 | 1055 | 1206 | 1190 | 1155 |

On an empty copy all six pages were 100-190 ms and `/today` was not slower, so the fault shows only with rows in the tables.

## Handoff

- Not measured: CI's own hardware and its copy (its /today 450-510 ms was reported to me, not reproduced); the 1.25 rule
  there needs three green runs in a row, which only CI can give.
- Seen, not fixed (not this cause): every page waits ~0.9 s on one query in `lib/queries-people.ts` `topics()` once there are
  40 classes (it is in the layout's list, so all pages pay it alike). Worth its own goal.
