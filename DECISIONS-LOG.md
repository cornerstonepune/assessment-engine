# Decisions log

Newest first. One line per decision: date, decision, why, source. Rejected alternatives get an ADR.

| Date | Decision | Why | Source |
|---|---|---|---|
| 2026-09-16 | Build the assessment module in full now; the rest of the Learning OS follows step by step. | Four real assessments per child already exist; a real trajectory is the fastest proof. | nimish (chat) |
| 2026-09-16 | Stack: Python engine + Supabase Postgres + self-hosted n8n + Next.js (ADR 0001). | Reuse validated code; one database; requested orchestrator. | nimish delegated: "you are the technical founder" |
| 2026-09-16 | Skill model: registry skill → rung → case tags (ADR 0002). Team taxonomy §12 adopted as the tag matrix. | No fourth taxonomy; coverage guaranteed by tags. | team taxonomy PDF; spec v0.1 §0 |
| 2026-09-16 | n8n orchestrates only; prompts, rules, thresholds are rows (ADR 0003). | Diffable, testable, evaluable. | spec v0.1 §7; nimish |
| 2026-09-16 | Phase 1 = legacy import of the existing 13 scans, before generation. | First real trajectory; first real test of vision reading. | scan check: 0/13 have markers |
| 2026-09-16 | Repo lives at `cornerstonepune/assessment-engine`, local checkout inside `~/cornerstone/`; parent folder is not a repo. | Org ownership; raw data and design docs stay outside git. | nimish (chat) |
