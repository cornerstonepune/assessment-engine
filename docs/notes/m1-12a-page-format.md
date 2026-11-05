# m1-12a: the new page format and the maker–checker (W1, gate N1)

## Verified
- Pure and database tests for the format, the maker–checker and the drafting run (101 pass locally on a copy of the schema): see the goal's criteria.
- No model call has been made. `k2_page_draft` v4 and `k2_page_check` v1 are inactive prompt rows (rule 7: active only after the dev re-draft is scored).

## What changed
- A draft is a list of steps (at most 8, each at most 14 words by code; the prompt asks for 12) and a thought: one idea line and 1 to 4 slips (a keyword of 2 to 4 words and a "how to spot it"). Limits are the config row `k2.format`.
- Code refuses, before the checker is paid for: a wrong shape, a step using a noun that some page of the band names as a material but this page's list does not (limit: it sees only nouns some page names), a `uses` entry not in the page's list, the house rules (gendered words, comparing children), identical levels.
- The checker (`k2_page_check`, Opus 5.5 at low effort, not Haiku) sees only the school's own words (never a part a machine drafted earlier) and the draft; it returns, per page, agree or disagree and a reason per fault. The maker revises the parts at fault once; the revised page is checked once more; a second fault stays with the checker's reasons for a person.
- The ledger's `page_part` proposal keeps the parts as lists and a `history` of each round (verdict, faults, a refused revision). The text columns are written from the lists (`k2_format.render`), so the site and the upload read what they read before.
- A page this maker (v4) has drafted is not asked again; an older maker's draft is (the 99 old drafts), and a part a machine drafted earlier counts as empty.

## Handoff
- Next (own PRs): apply a redraft over the earlier machine drafts (not the school's, not a person's) and the list form stored for the screens; edit/revert/confirm routes; skill links with offered skills; a measured forecast.
- The forecast now includes the checker round and the revisions (`est_revise_share`); numbers are still assumed until the dev run measures them.
- The dev stage reads 60 pages (`dev_pages`), the orchestrator's number.
