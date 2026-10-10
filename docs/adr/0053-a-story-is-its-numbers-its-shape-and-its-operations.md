# ADR 0053 — A story is its numbers, its shape and its operations

**Status:** accepted (2026-10-10, slice AS2 of BUILD-ORDER "Inserted now: multiplication and division"). Takes up the
option ADR 0011 rejected, its trigger met.
Goal: goals/as2-a-story-is-its-shape.yaml

## What happened

A story's key was its numbers alone (`WP1` + a, b, op; `WP2` + a, b, c), so "7 − 3" as a take-away, as a comparison and
as a start no one knows was one question. On a level of small numbers the story cases listed first took every pair:
filled whole, as `bank refill` fills it, SUB.1D1D's Advance (seven subtraction stories over 36 pairs, 9 each asked) held
no W11, W02 or W03, and ADD.1D1D's (four addition stories over 72 pairs, 24 each asked) no W06. Three seeds each, the
same (STATE.md "AS2 — measured before the build"). ADR 0011 named this option and its cost — "it rewrites the key of
every word problem already stored" — and the day "a rung needs far more items than its numbers allow". That day came.

Building it found two more:

- A story's shape was never stored on it: `tags.derive` read it back from the words through the template that wrote
  them. A story a person reworded matches no template, so the next `bank relabel` (update-live runs one every time)
  took its shape and its cases away, and `bank refill` retired it as "outside every case the level holds".
- A two-step story's key held no operation, and three shapes have two arithmetics each: UNKNOWN_FIRST (a − b + c and
  a + b − c), EXTRA_INFORMATION (a − b, a + b), CONSTRAINT (a − b + c, (a − b) ÷ 2). Two different questions shared a
  key; the second was dropped as already held.

## Decision

1. **A story's spec holds its shape and its operations, so its key does** (`words.story_spec`): a one-step story
   `{a, b, op, structure}` (and its `table`), a two-step `{a, b, c, structure, ops}`, `ops` its template's operations
   in order. Its words are not part of it: two templates of one shape and one arithmetic are two wordings of one
   question. A test holds every pair of templates that key the same numbers alike to one answer, so a template added
   later that breaks this fails before it can lose a question.
2. **Both ways into the bank key a story alike.** `verify.to_item` keys a story by the template that wrote its words
   (the sampler's are templates'); a sentence a model wrote names no shape and keeps the key of its numbers.
3. **Every story stored before is keyed again, once,** by `engine bank rekey`, which `bin/update-live` runs first in
   step 5, before `bank relabel` reads a story's shape. It finds a story's template from its words (`template_of`),
   changes no word, number or answer, and writes each change as a row of `item_key_change` (append-only).
4. **A key a question had still leads to it.** One rule, `current_item_key()` in SQL, follows `item_key_change`; every
   reader of a key that may be old uses it: a printed copy's key file, whose boxes the reader finds by key
   (`copies.paper`), `question._row` (the question page's engine side, a person's rewording or removal, a proposal
   decided), `inventory.flag`, the website's question page, a gold file loaded. A row that may be changed follows its
   question in place (`item_review.ref`, `gold_finding.item_key`); a row in an append-only ledger never does
   (`bank_proposal.subject`), and is read through the rule — the "already proposed" check included. ADR 0050 rejected
   changing a stored key in place because "a printed paper would no longer read as it did"; through this rule it does.
   `item_key_change` names its question with no cascade: a cascade from a deleted question is a DELETE on the ledger,
   which its trigger refuses even with no row to remove, and a question whose key changed is never deleted.
5. **A rewording keeps its own key** (its words are part of it, `question.correct`) and takes the shape of the story it
   rewords, followed back through `corrected_from`; it copies its story's spec from then on, so its shape travels
   with it.
6. **The same story twice** — the bank already holds the key a stored story would take — is the older row retired,
   through the path a person's flag takes, with a note naming the one kept.

## Rejected

- **Words as part of a story's identity** (ADR 0011's option as written). The same numbers in the same shape with other
  nouns is the same question to a child; keyed by its words, a level would fill with near-copies and still starve.
- **Retire every stored story and draw again.** Thousands of printed and answered questions would leave the bank and
  every worksheet holding one would be dealt again, for no change in any question.
- **Rewrite a proposal's subject.** `bank_proposal` is append-only: a proposal is what the engine said then. The key
  change is itself a ledger row, and the proposal is read through it.
- **Keep both keys at the door**: insert a new story only if no old-style key of the same story exists. Every reader
  of a key would carry the old scheme for good.
- **The shape in the key but not in the spec.** The key would stop being a function of the spec, `bank recheck` could
  not rebuild it, and a rewording would still lose its shape.

## Consequences

- A level of small numbers holds each shape it lists: the scenarios fill SUB.1D1D's Advance (108) and ADD.1D1D's
  (216) whole with every case held.
- The same two numbers can now be two stories on one worksheet (a take-away and a comparison); a child reasons
  differently in each, and the dealer does not look at numbers.
- Every stored story's key changes once on live. A bookmark, a gold file or a proposal naming an old key still finds
  its question.
- `bank recheck` rebuilds a one-step story with its shape (its spec's `structure` is one `to_item` makes), so every
  one-step story stays inside the audit.
- The rehearsal on a copy of live runs every command update-live runs, in its order, held by a test
  (`test_update_live.py`): the two lists had drifted, and the first rehearsal of this slice passed without `bank rekey`.
