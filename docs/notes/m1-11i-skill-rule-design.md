# m1-11i: pass a mapping only when every skill came from the examples (design, no code)

Status: a proposal for the orchestrator to decide. Nothing in the engine changes with this note.

## What the replay says, and what it cannot
From the live `map_replay` of the latest dev run, as read by the orchestrator (figures relayed, not re-run here):
- per skill, by place in the list: 1st right 86 of 96, 2nd 46 of 78, 3rd 10 of 20;
- per skill, by whether the proposer was shown it in an example: shown 87 of 110, not shown 55 of 84;
- an activity passing when every skill it names was shown, with confidence at least 0.7: 33 activities, 30 right (0.909); at
  least 0.75: 23 of 23.

Read these with three cautions:
1. **Small numbers.** By my arithmetic (Wilson, 95%; verify before quoting) 30 of 33 is about 0.76 to 0.97, and 23 of 23 is
   about 0.86 to 1.0. A point estimate of 0.91 or 1.0 does not show 0.90 holds. One run of 100 activities cannot.
2. **The bar was picked on the same data it is scored on.** 0.70 and 0.75 are the best-looking bars of a table; that is
   optimistic by construction. Only a set not used to choose it can say what it does.
3. **It may be choosing easy activities.** "Every skill was in the nearest examples" passes the activities most like ones
   already mapped, which people need least help with. That is fine for safety; it also means the share saved is small.

**It does not reach the auto-pass bar.** At 0.7 about a third of activities pass (33 of 100, and the 10% audit sample comes
off that); at 0.75 about a quarter. The bar `eval.curriculum_map.auto_passed` is 0.60, set before any data. Two ways, and the
choice is Nimish's: lower that bar to what the rule can honestly do, or accept that two thirds of activities still go to a
person. I would not tune the rule to chase 0.60.

## The rule
An activity's skill proposal passes on its own when ALL of:
a. code found nothing wrong (as now);
b. every proposed skill is among the skills of the examples the proposer was shown for that activity (new, code, read from
   the question that was asked, the way the replay reads it);
c. the proposer's confidence is at least X (the existing row `map.min_confidence`, X chosen below);
d. it is not in the audit sample, and its kind is not stopped (as now).

The checker's verdict stays a gate as it is: it agreed 46 of 88 right against 5 of 9 for disagree, no signal either way, and
it agreed on 88 of 97 proposals, so dropping it changes little. It can come out only after a fresh run says the same; that would also cut about two
thirds of the calls.

**Settings, not code (rule 1):** `map.min_confidence` stays the bar and is set to X; one new threshold row,
`map.require_examples` (1 or 0, unit "flag"), switches (b) on, so the rule can be turned off without a deploy. Seeded in
`supabase/seed/thresholds.json` with a description, as the others are.

**Choosing X before the next run:** X = 0.70 (from the dev run), written down now and not changed after the held-out run.
If the held-out run says otherwise, X is tuned on a third, disjoint set or not at all.

## The skills that are not passed: "add this skill?"
Two readings of the brief; I recommend A.
- **A, split.** The skills that were shown form one `skill` proposal (auto_passed if c holds, else needs_person). Each skill
  that was not shown becomes its own proposal of a NEW kind `skill_offer`, needs_person, reason "not among the skills of the
  nearest examples". One proposal per skill, keyed `(kind, activity, skill)` in `map_ledger.proposed()` the way `lo_skill` is,
  so a "no" is not asked again. Applying one inserts the same `activity_skill` row (`source = 'machine'`).
- **B, hold.** If any skill was not shown the whole proposal waits for a person.

Why A: the replay says 55 of 84 skills the proposer was not shown were skills people also linked (about 65%). That is a
good offer rate, and B would throw the 87 right ones in with them. Cost of A: more rows for people to answer (up to 84 offers
per 100 activities on the dev run).

**Where a person sees an offer: nowhere yet.** `curriculum_proposal` is read by no page of the site (checked in apps/web);
the only list of what waits is the command `engine curriculum review`, which the school's staff cannot run. The rule
changes what is queued, not who can answer it. A screen (per skill: the activity, the offered skill, yes or no, who answered
by id) is its own brick, following the drafted-pages review, and must exist before the rule is switched on for anyone.

## How to test it
1. Tests first, no model: `decide()` with the new inputs (all shown and confidence at least X passes; one not shown becomes an
   offer; one proposal per offered skill and the same key never again; the flag at 0 behaves as today); the stored dev run
   re-decided under the rule reproduces the replay's tables.
2. **A pass bar written before the run:** on the held-out set (all the gold except the 100 dev activities; its size I do not
   have, it is the count of mapped activities less 100), with X fixed: precision of the passed at least 0.90 AND the share
   passed reported with its interval. If the interval's lower end is under 0.80, the answer is "not yet", not "pass".
3. The run is `map_held_out` with proposer v3 (about INR 1.3 per activity from the dev run's INR 132 for 100; the held-out
   size multiplies it). `map_replay` then prints every table and the rule can be evaluated offline, free, as often as needed.

## Are the 3 schema rejects gone with the vendor-held schema?
Not knowable without a live call. The request shape comes from the docs and the SDK's types, never from a live answer. What
could still go wrong: the API refuses the schema (HTTP 400, nothing spent); the reply stops at the token limit; a refusal. The
extra-field cause is closed by construction if the API holds the reply to the schema.

**Smallest live call:** a probe, `engine curriculum map-probe`, that asks proposer v3 about ONE dev activity through the same
adapter and the `dev_eval` stage (so its cap and ledger apply), writes only the flow_run row, and prints: accepted or refused
(and why), tokens in and out, cost, the reply's field names. Roughly INR 1 (an estimate: one proposer call of the dev run).
It tests the request shape before INR 130 is spent. It cannot test the 3% rate, which needs at least 100 calls: that is the
full run.

Why not "start `map_dev` and cancel": I am not certain a cancelled workflow run stops the command on the server; worth
verifying before relying on it. If the API refuses the schema the first call should fail at no cost; if it accepts, the
whole INR ~132 may be spent.

## Handoff
- Needs a decision: reading A or B; whether to lower the 0.60 auto-pass bar; whether to build the probe (small, one
  allowlisted choice, a few tests) before the next `map_dev`.
- Not built, not tested: everything above.
