# M0-01 Rename follow-through (2026-11-03)

No workflow or gate moved: this is plumbing after the repository's rename to cornerstone-platform.

## Verified
- The report button files issues in `cornerstonepune/cornerstone-platform` (`apps/web/lib/github.ts`, and the fake GitHub
  in `apps/web/tests/github-server.ts`). The website's test (`u70-report-a-problem.spec.ts`) was NOT run here: the
  website's packages and the full local stack are not installed in this session. Run it in CI.
- The real pooler address is gone from the repository (a search of every file for the pooler's host name finds nothing). The Phase 0 plan's
  example now reads `postgres.<project-ref>:<password>@<pooler-host>:5432`. No password was touched; live was not connected to.
- `engine past`, on a local database built from the repository alone (`bin/testdb fresh`; Docker is not available here),
  before (main 7a6d902) and after this branch, identical:
  `evidence 0 rows / states 0 rows / scored 0 rows`, each checksum `d41d8cd98f00b204e9800998ecf8427e`
  (the hash of nothing). That copy holds no children's answers, so this shows the command runs and the branch moves no
  data; it does not show a real child's history is unchanged. Nothing in this change touches data or the engine's code.
- Left alone on purpose: every `~/assessment-engine` server or Mac path, `deploy/go-live.sh`, `bin/update-live`,
  `deploy-engine.yml`, `engine-logs.yml`, `supabase/config.toml`, migrations, historical docs, ADRs, `apps/web/results.json`.

## Handoff
- Not met until Nimish clicks in Vercel (Project > Settings > Git: reconnect cornerstonepune/cornerstone-platform; Settings >
  Deployment Checks: the required check is named `live database`) and the next merge is seen to go live.
- The live database's project reference still appears in STATE.md, DECISIONS-LOG.md and the Phase 0 plan. Not a password.
  Left, as the task named only the pooler address.
