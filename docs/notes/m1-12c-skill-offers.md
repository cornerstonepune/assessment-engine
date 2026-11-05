# m1-12c: a skill passes only if an example showed it; the rest are offered (W1, gate N1)

## Verified
- The rule, the offers, the list and the answer, and the routes: tests/test_map_offers.py, test_skill_offers.py, api/test_offers_routes.py pass on a local copy (the new migration applied by hand). Nothing run live; no model call.

## What changed
- `map.skill_min_confidence` = 0.70, `map.require_examples` = 1, `map.use_checker` = 0 (threshold rows). With the rule on, a skill proposal's skills split: those an example the proposer was shown carried stay one `skill` proposal (decided as before, with the 0.70 bar for a skill); each other is a `skill_offer`, one proposal for one skill, needs_person. With no skill shown there is no main proposal, only offers. Rules off: as before.
- The second model (Haiku) is not asked while `map.use_checker` is 0: its verdict then does not decide.
- Migration `20270107090000_skill_offers.sql` adds the kind `skill_offer`. `apply` can be limited to one proposal.
- `skill_offers.waiting` / `answer` and routes `POST /curriculum/offers/list | answer` (staff only). A yes adds that proposal's skills as the machine's links naming the proposal (revertible); a no closes it; both keep the person's id.
- `Proposal` and `Rules` now live in `map_check.py` (re-exported from `map_agents.py`, which was at its ceiling).

## The data shape the offered-skills screen reads (POST /curriculum/offers/list {actor})
```
{ offers: [ { id, kind: "offer" | "skill",       // offer: a skill no nearest example carried; skill: a shown skill under the bar
              activity: {code, name, section},
              skills: [ {code, name} ],          // what is asked to be added
              also:   [ {code, name} ],          // for an offer: the skills proposed beside it that did pass
              confidence, reason } ] }
```
`POST /curriculum/offers/answer {actor, id, yes, why}` returns the list that is left. 409 if the proposal is not waiting; 403 if not staff.

## A no is never asked again (orchestrator, 2026-11-05)
- `map_ledger.asked` = every (activity, skill) ever offered, whatever became of the offer, plus every skill of a skill proposal a person turned down. `propose` and `split` leave those out, so a rerun of `engine curriculum propose` offers nothing already waiting, added or refused; a proposal whose every skill was asked about is not made at all. Tested by a rerun after a refusal and after a yes.

## Switches
- The offers routes do not look at the educator or voice switches. Acceptable for now: engine key plus a signed-in staff check. They go behind the shared `educator.preview_roles` helper when the 4b session lands it.

## Limits
- The dev run's numbers behind X are one run, the bar chosen on the same data, 33 activities: see m1-11i. The skills offered will be many (up to 84 per 100 activities in the dev run); a person's time is what the screen decides.
- The score printed by `engine eval curriculum_map` counts only the `skill` proposals, so offered skills are not in it; the replay's `skill_split` table is where their hit rate is read.

## Handoff
- Next: the measured forecast command; then every stage is dispatched by the orchestrator. After the held-out run: counts per part per activity (K2 871) and the data shapes, as asked.
