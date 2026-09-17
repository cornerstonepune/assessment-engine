# Decisions log

Newest first. One line per decision: date, decision, why, source. Rejected alternatives get an ADR.

| Date | Decision | Why | Source |
|---|---|---|---|
| 2026-09-17 | Vision reading uses Gemini Flash free tier for the pilot, behind an adapter that masks the child's name before any image is sent (ADR 0004). Revisit at the first non-founder class run or at production. | Free and fast to start; masking makes the free tier's training terms acceptable because what leaves the machine is anonymous. | nimish (chat) |
| 2026-09-17 | Supabase project `cornerstone-cloud` (ref `ruznbyngtfjsaymuylhm`, ap-south-1) is the shared backend for every Cornerstone product, not just this engine. CLI access via a repo-scoped `SUPABASE_ACCESS_TOKEN`, because the machine's default Supabase login is a different personal account. | One database is the point — "how is this child doing" must be one join. | nimish (chat) |
| 2026-09-17 | Per-child adaptive assignment is in scope from Phase 2: the nightly rebuild prescribes each child's next sheet (rule in SPEC §5, thresholds as rows); the class matrix is only the fallback for children without enough evidence. Reverses SPEC §15's earlier exclusion. | Four assessments per child give the graph enough evidence on day one; a class-level sheet would waste it. | nimish (chat) |
| 2026-09-16 | Build the assessment module in full now; the rest of the Learning OS follows step by step. | Four real assessments per child already exist; a real trajectory is the fastest proof. | nimish (chat) |
| 2026-09-16 | Stack: Python engine + Supabase Postgres + self-hosted n8n + Next.js (ADR 0001). | Reuse validated code; one database; requested orchestrator. | nimish delegated: "you are the technical founder" |
| 2026-09-16 | Skill model: registry skill → rung → case tags (ADR 0002). Team taxonomy §12 adopted as the tag matrix. | No fourth taxonomy; coverage guaranteed by tags. | team taxonomy PDF; spec v0.1 §0 |
| 2026-09-16 | n8n orchestrates only; prompts, rules, thresholds are rows (ADR 0003). | Diffable, testable, evaluable. | spec v0.1 §7; nimish |
| 2026-09-16 | Phase 1 = legacy import of the existing 13 scans, before generation. | First real trajectory; first real test of vision reading. | scan check: 0/13 have markers |
| 2026-09-16 | Repo lives at `cornerstonepune/assessment-engine`, local checkout inside `~/cornerstone/`; parent folder is not a repo. | Org ownership; raw data and design docs stay outside git. | nimish (chat) |
