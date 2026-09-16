# ADR 0003 — n8n orchestrates; the engine and the database think

Date: 2026-09-16. Status: accepted.

## Decision

n8n holds three workflows — F1 generate-weekly, F2 capture-and-mark, F3 nightly — consisting of
triggers, HTTP calls to engine endpoints, waits for human confirmation, Drive and notification
I/O, retries, and `flow_run` writes. Prompts live in the `prompt` table; blueprints, marking rules,
and thresholds in their tables; all logic in the engine. Legacy import of non-QR paper is an
engine CLI, not a workflow. Workflows are exported to `n8n/workflows/*.json` and reviewed in
pull requests.

## Why

- Requested explicitly, and it is the right tool for "trigger → step → human confirm → write":
  a coordinator can see and re-run a flow without reading code.
- Logic inside n8n nodes cannot be diffed, tested, or evaluated. Keeping every prompt and rule in
  the database with a version keeps them reviewable and lets an eval gate them.
- Self-hosting keeps children's work photos on infrastructure the school controls, which is
  easier to defend under DPDP than a third-party cloud instance.

## Rejected

- **Inngest / Trigger.dev (code-defined workflows).** Better version control, but no visual
  surface for a non-developer coordinator, and the operator asked for n8n.
- **n8n Cloud.** Faster to start; photos of named children would transit a third party.
- **A cron + a Python queue, no orchestrator.** Simplest, but the "human confirm before write"
  wait and the notifications would be re-implemented by hand, badly.

## Consequences

The exported JSON is the source of truth for a workflow; editing in the n8n UI without exporting
is a defect. Node names must be verified against the installed n8n version before F1–F3 are
built; the spec's node lists are flow logic, not a build sheet.
