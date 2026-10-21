# second-reader-every-guess — a second opinion where the box reader guessed

Nimish, 2026-10-21 11:45 UTC, "yes", to PR #244's question: should the second reader also give a second opinion where
the box reader already guessed? Goal: `goals/second-reader-every-guess.yaml`. ADR 0091 (amends ADR 0032 §4). W3, the
reader-learns gate.

## Verified

| Claim | Command | Last output |
|---|---|---|
| A box guess the reader did not stand behind is read again with the child's samples; agreed, it is unchanged; not, it waits with both readings; it never settles, never sees the question; a failed call is not a wrong reading; off until its row says so | `cd packages/engine && uv run pytest -q -p no:cacheprovider tests/test_second_reader.py` | 11 passed |
| The queue and the paper show "Two readers disagree" with both readings | `cd apps/web && npx playwright test tests/s4-validation-queue.spec.ts -g "second reader\|two readers"` | 2 passed |
| The code against the map, the promises, lint | `bin/check` | 28 passed |

**On live** (Actions → engine eval → read_with_examples, this branch; runs 39603709261 and 39605855114, 21 Oct 12:57
and 13:12 UTC). Counts only.

| What | Number |
|---|---|
| printed papers read in boxes, 26 Sep–16 Oct | 34 papers, 421 answers |
| answers the box reader guessed (would get a second opinion) | 116, one call each: about 3.4 a paper |
| of those, settled without a person's word | 0: a second opinion sends no extra answer to a person |
| the box reader's guess right / wrong (by what a person typed) | 82 / 34: 34 is the most it could catch |
| the second reader's eval on those 116 | **not scored**: 116 of 116 calls failed, "ANTHROPIC_API_KEY is not set", fallbacks failed too (232 failed calls recorded today), Rs 0 spent |
| one call's cost when it worked (49 calls, 22–29 Sep) | Rs 0.28 on average, Rs 0.73 at most, ~3,000 tokens in: roughly Rs 1 a paper (approximate) |

Run 39602936737 died earlier when the SSH connection dropped during minutes with no output; the workflow now keeps it
alive. That run's model calls were rolled back with it (none reached the model: the key was missing).

## Handoff

- **Live:** nothing changed. Not merged, not deployed. `read.second_opinion` ships at 0, so the reader behaves exactly as
  today after merge.
- **Blocked on Nimish:** the live engine has no model key. Until one is set, the second reader does nothing on live at
  all, for what the first reader gave up on as well. Every read of a page where it is asked will spend time trying five
  models and fail quietly.
- **Next, once the key is set:** run Actions → engine eval → read_with_examples on this branch (or on main after merge).
  It scores the second reader on the 116 checked box guesses: how many of the 34 wrong guesses it would have flagged,
  how many of the 82 right ones it would have questioned. Record it in DECISIONS-LOG, then set `read.second_opinion`
  to 1 if it earns it.
- **Not certain:** why the fallback models failed. The error was cut at 240 characters before their reason.
