# HANDOFF — for the next session

Read `BUILD-ORDER.md` first: it says which workflow we are on and what "done" means. Then
`STATE.md` for what is verified. This file only says where the last session stopped.

## Where we are: W1 — build the bank. **All six gates closed (2026-09-20).** W2 opens.

| Gate | State | The command that says so |
|---|---|---|
| 1 every rung has a ratifiable spec | **closed** | `engine ratify --by "Nimish Shah"` → `17 ratified, 0 still draft`, then `2 ratified, 0 still draft` after two lists were corrected (2026-09-20); `select status, count(*) from skill_set group by status` → `ratified 17` |
| 2 every unit is rich | **closed** | `engine bank coverage` → `68 units, 0 under their target` |
| 3 a new topic by rows | **closed** | multiplication: a rung row, a skill-set row, one sampler; 200 items |
| 4 code verifies, the validator judges language | **closed** | `engine eval language_review` 6/6, `pedagogy_review` 5/6; `bank recheck` → 0 mismatches |
| 5 it runs as a workflow | **closed, one honest gap** | F1 in n8n; `python n8n/lint.py n8n/workflows/*.json` → ok; pinned run routed correctly. The live end-to-end run still needs the engine reachable from n8n Cloud |
| 6 cost is known and near zero | **closed** | `select sum(cost_inr) from flow_run` → **₹1.29** against a ₹50 bar |

Bank: **3,565 live questions**, 68 units, 17 skill sets, 17 rungs, 244 skills loaded.
Suite: **291 passed**. Every number above is a command in `STATE.md`, not a description.

Gate 1 closed on Nimish's own signature, not Aseem's (ADR 0013): he read the sets and said ratify
so W2 is not held on other people's calendars. Ratification is per-version — the trigger withdraws
it the moment anyone edits a spec's content — so the school's corrections remain the normal path
and re-open the signature on whatever they touch.

## How to tell if anything is broken, before anything else

```
~/cornerstone/assessment-engine/bin/engine goal w1-build-the-bank     # 10 scenarios + 5 criteria
~/cornerstone/assessment-engine/bin/engine audit                      # 12 invariants over every row
```

Both must print `GOAL ACHIEVED` / `0 violations`. They run from any directory. A session that changes
anything in W1 runs them before it claims to be done, and W2/W3/W4 each need their own goal file
written **before** their work starts (ADR 0015) — for W3 that means the reading-accuracy bar against
the 84 real sheets, as a number, first.

## Next action

1. **Decide whether to apply the engine's mistake lists.** `engine bank misconceptions <set>` shows
   what code computed and what the model added; nothing is stored until `--apply`, which unions the
   list into the set (it can never drop a curated code) and withdraws that set's ratification. Not
   applied anywhere yet. Numbers to decide on: the model adds ~0 on a pure-arithmetic set (code has
   it covered), 4 on `WORD.1_2STEP`, 5 on `REASON.EXPLAIN`, at ₹0.53 a set.
2. **One style decision is open and it is yours** (`AISLOP.md`: config is authoritative, don't edit
   without consent). Every engine `.py` trips aislop's `python-formatting` warning because the repo
   never adopted `ruff format`. Measured: 536 diff lines over two files, and it explodes the
   misconception registry from one readable line per mistake into five. Either adopt the formatter
   and accept that, or record the exception in `.aislop/config.yaml` with the reason.
3. **Nimish's instruction, 2026-09-19, not yet done: W1's screen talks like a machine.** His words:
   "It can't be so robot-looking, so programmatic in nature, and we'll need to provide small little
   examples behind a lot of these things." Specifically, on `/skill-sets/[code]`:
   - **Formats** are shown as a label plus a raw code (`bare_sum`). Each needs a one-line worked
     example of the shape — `47 + 38 = ___` for a horizontal sum, the column grid drawn, `4_ + 8 =
     52` for a missing number — rendered from the format, not typed into prose.
   - **The four difficulties** are shown as the checkable rule in boxes (digits, exchanges, zeros).
     A teacher should first read one plain sentence — "two 2-digit numbers, one exchange, answer
     under 100" — with a real example question under it, and the boxes underneath for whoever wants
     them. The sentence is generated from the `check`, so it can never drift from the rule.
   - **Misconceptions** lead with `M_NOCARRY` and then the name. Invert it: the plain sentence and
     the worked example first (`47 + 38 → 75`, already in the row's `description`), the code kept
     as small provenance text, because the code is the join key the reader and the graph use and
     must stay visible somewhere.
   - Same pass over learning objective and philosophy wording.
   This is presentation only: it must not write to `skill_set`, or it withdraws the ratification it
   is meant to make legible. Ask him whether it goes before W2 or alongside it.
4. **W2 — assemble and print.** Now unblocked. Note `BUILD-ORDER.md`'s parked item: W2 is where the
   single **Assessment Specification** contract should land (external proposal §4), because that is
   when a second consumer of the shape appears.
5. **The three pedagogy questions ratification did not answer** — they are Neha's, Achal's and
   Aseem's, and the engine is not blocked on them:
   - **The pedagogy reviewer disagrees with our format mixing.** On `SUB.2D.EXCH` Hard it rejected
     the missing-number and word-problem items, arguing they test inverse reasoning and application
     rather than the exchange procedure. If they agree, those formats move to their own bands; if
     not, the reviewer prompt needs a line saying a rung's skill can be tested in applied form. The
     verdicts are in `item_review`.
   - **The gold set is provisional** (`supabase/seed/validator_gold.json`): a 2-digit sum filed in a
     3-digit band — *revise* (wrong band) or *reject*?
   - **The G1 floors.** `ADD.1D.WITHIN10` holds 22-24 per band because "within 10" has that many
     distinct questions. Confirm that is acceptable, or widen the rung (ADR 0011).
6. **Gate 5's remaining gap, whenever the pilot needs it:** n8n Cloud cannot reach
   `http://engine:8000` on a laptop. Deploy the engine or tunnel to it; `deploy/compose.yml`
   already runs both together where they share a host. The workflow itself needs no change.
7. **Two credentials must be created by hand in n8n** before F1 can run — see `n8n/README.md`:
   an `httpTemplatedCustomAuth` holding `ENGINE_KEY`, and an SMTP sender.

## Blocked on Nimish

- The three pedagogy judgment calls above — Neha, Achal and Aseem. Ratification itself is done
  (2026-09-19, Nimish's signature on all 17; ADR 0013), so nothing in the engine waits on it.
- Standing: Achal's and Neha's emails for `app.staff`; rotate the database password; `AUTH_SECRET`
  on Vercel if unset; the n8n owner account when F1 is wired (W1 gate 5).

## Traps — do not repeat

- **Building out of order.** Each of the three sessions before 2026-09-19 opened a new area before
  the last was done. `BUILD-ORDER.md` rule 1 exists because of this.
- **Pivoting from chat.** QR was nearly built next because one sentence was misread. Restate, get
  a yes, write it into `BUILD-ORDER.md`, then build.
- **Answering "is X built?" with a mechanism instead of a number.** The bank was 2 of 64 units at
  the start of 2026-09-19 and 68 of 68 units by the end of it, from `engine bank coverage`.
- **Inventing a code verifier where none exists.** R7, R11, R13, X1, X2 have a claim (strategy,
  reasoning, an explanation) code cannot check — say so in the row's `philosophy` and route through
  the validator's template-level check plus its ≤5 % sample (ADR 0009/0010), never a fabricated
  numeric check standing in for a judgment call.
- **A skill set's `formats` list must be a subset the intended generator actually renders** — if
  none of them are among the sampler's four known shapes, `bank._sampled` now refuses rather than
  silently rendering plain column arithmetic under the wrong skill set. This bug existed latent
  since Sept 17 and was only reachable once R11/X2-shaped rows existed; check for the same class of
  mistake before wiring chunk B's native formats.
- **Item identity ignores skill_set/difficulty** — two bands with the same effective rule compete
  for the same items instead of each getting their own 50. Now caught rather than worked around:
  `engine load --check` refuses two bands of one skill set that declare the same region, and
  `bank recheck` re-measures every item against the band it claims. Giving each band
  a genuinely distinct rule, which is exactly what R1/R2 above still need.
- Still true, technical: `roster` is an unused import in `engine/legacy.py` (pre-existing, left
  alone); Docker's credential helper hangs from a non-interactive session (STATE.md N3.2 has the
  workaround); an idempotency key derived from a generic request body is not private to a test.
