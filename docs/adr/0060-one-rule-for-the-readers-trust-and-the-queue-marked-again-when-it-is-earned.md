# ADR 0060 — One rule for the reader's trust, and the queue marked again when it is earned

**Status:** accepted (2026-10-10, slice NY2 of BUILD-ORDER "NY1 and NY2"; W3 by Nimish's exception).
Goal: goals/ny2-the-queue-shrinks.yaml

## What happened

Nimish, 2026-10-10: *"The system keeps learning from the number of data points that we keep validating, and the number
of data points that we then need to validate becomes lower."* ADR 0032 made that the design: a kind of question is
settled by the reader alone once 95% of its last fifty checks matched a person. Measured the same day (STATE.md "NY2 —
measured before the build"):

- **Trust had two owners.**
  - The engine decided it in Python, ordering checks by when the paper was read and then by question.
  - The website decided it again in its own SQL, ordering by when the paper was read alone. Every answer of a paper
    shares that moment, so where the fiftieth check fell inside a paper, the website's window was arbitrary.
  - Both wrote the fifty into code.
- **Earning trust moved nothing.** An answer held only because its kind was not yet trusted was marked again only by a
  command no one ran. So the queue could not fall when trust was earned.
- **No screen showed whether the queue was falling,** nor how far a kind was from trust.

## Decision

1. **One rule, in the database.**
   - `checks_to_trust(recent, size, bar)` and the `kind_trust` view (migration 20261103090000) decide each kind's
     standing: its newest checks the reader stood behind, how many matched, whether that is trust, and the right checks
     still needed.
   - Checks are ordered newest first by when the paper was read, then by question, then by answer, so the window is the
     same every time it is read.
   - The window is a row, `marking.agreement_window` (50). The bar stays `marking.agreement_gate` (0.95).
   - The engine (`profiles.kind_trust`), `engine read report` and the website (`readerReport`, Today) all read the
     view. None decides it again.
2. **Checks to trust** is the fewest right checks, one after another, that make the window trusted. Zero means trusted.
   At most the window: a window of right checks alone is always trusted.
3. **A check marks again what trust now settles** (`again.trusted`).
   - It re-marks every candidate of every trusted kind from what was read, never asking the reader again.
   - A right answer held only for trust settles. A wrong or a blank still waits for a person (ADR 0029).
   - A spot-checked right answer still waits: it is the same sample as when it was read.
4. **The check and the re-mark share a transaction** when the check comes through the engine (`POST /capture/correct`).
   A paper signed off through the website's SQL asks `POST /capture/trusted` straight after.
   - If the engine is not answering, the sign-off stands and the page says so. The next check marks the answers again,
     and `again.trusted` is safe to repeat.
5. **Marking again starts from what the reader said.**
   - A hold's reason ("read as …") is written by marking, never by a reader (`profiles.doubted`).
   - So `mark_read` removes an earlier hold's reason and guess before it marks. Otherwise an answer would settle while
     still saying a person checks it, and the website would go on treating it as waiting (`queries-read.held`).
6. **Today shows the queue week by week** (`answer_standing`, the one definition of where an answer stands): read,
   settled by the engine alone, checked by a person, still waiting, and the share that needed a person. It also shows
   how many kinds are trusted and how near the nearest one is.

## Rejected

- **Two rules held equal by a test.** They had already drifted: the website's ordering differed. One rule cannot drift.
- **Marking the queue again on a schedule.** The queue would stay up until the next run. "The moment a kind earns
  trust" is the check that earns it.
- **Re-marking only answers whose reason says "until the reader is trusted".** That ties the rule to one sentence's
  wording. Re-marking every candidate of a trusted kind gives the same result and changes only what trust changes.
- **Moving the sign-off itself into the engine.** It would change how a paper is signed off, which this slice does not
  need. The sign-off stays SQL (`confirm_results`) and asks the engine for the re-mark after it.
- **Holding settled answers again when a check takes a kind below the bar.** `again.trusted` marks again only kinds that
  are trusted. An answer settled while its kind was trusted keeps its mark, as the rule stood when it was read. New
  readings of that kind wait for a person again. Holding them back would take settled marks from children without a
  person looking.

## Consequences

- The queue falls only as fast as the reader gets more right. On live, no kind is trusted yet: columns are nearest, at
  47 of their last 50 against 48 needed. NY2 makes that visible; it cannot make it so.
- Every wrong and every blank still waits for a person, whatever the trust, until a second reader is trusted (ADR 0029).
