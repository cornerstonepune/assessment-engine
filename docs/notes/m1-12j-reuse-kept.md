# M1-12j: do not pay twice for a first draft already paid for

## Verified
- Free replay after #430 (run 24): 51 of 59 kept first drafts pass the judge (no paid call). Remaining refused words are real props (blocks, colours, box, picture).
- `colour` and `colours` are one word in the matcher (`k2_batch._stem`, tested since #428). The replay printed the surface word, so two lines appeared; it now counts the stem.
- New: `engine curriculum draft --stage S --dev --use-kept` reads, for each page still wanted, the first kept maker reply the judge accepts (`k2_replay.kept_drafts`),
  uses it as the maker's answer (once), and asks the checkers and the revision as for any draft; the ledger row is the one a full run writes, with `history[0].reused = true`.
  Pages with no kept draft go to the maker. Run choice `draft_dev_kept` (spends); `forecast` also prints the kept-draft figure.

## Handoff
- Estimate for the paid dev stage and the rest: in the message to the orchestrator (maker measured, checkers assumed from config).
- Not measured: checker cost per page (the checkers have never run), the share of pages the checker sends back, how often Opus catches an invented prop.
