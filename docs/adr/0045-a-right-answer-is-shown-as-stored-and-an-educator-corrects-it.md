# ADR 0045 — A right answer is shown as stored, and an educator corrects it for every child

**Status:** accepted (built on Nimish's words of 2026-09-30: "the key can be changed by an educator, not an issue.
also in any correction, the system should show what the right answer is as stored in the system; that would remove
any suspicion or confusion and make it easier to spot any system issue as well")
Goal: goals/s26-the-right-answer-shown-and-corrected.yaml

## What happened

On the live Marking page of the Grade 4 September Week 1 paper, question 4A read "48 + 35 =". Nimish typed 78 for it,
and it was marked wrong. He asked for a way to change the right answer for every child.

The key was right. 4A is the box after "48 + 35 =", key 83, and it was empty on that paper. The 78 was in the number
line's first box, 4B, whose key is 78. The card showed the question but not the answer it was marked against, so
nothing showed that 78 belonged to another box. Changing 4A's key to 78 would have marked wrong every child who wrote 83
there.

## Decision

1. **Every answer a person checks shows its right answer as the engine stores it** (`keys.shown`,
   `GET /capture/{id}/keys`). This covers the paper page's cards and the one-at-a-time queue. The answer is shown as:
   - the key itself;
   - the equation a box of an equation is marked by ("any answer that makes 638 = 600 + [5a] + [5b] true");
   - "a person judges this one";
   - and, when an educator changed it, from what and by whom.
   If the engine is down, the page shows the key it read itself.
2. **An educator changes a paper question's right answer for every child, on any answer to it** (`keys.change`,
   `POST /paper/key`, "Is the right answer wrong? Change it for every child"). Any educator may; the change is kept in
   their name.
3. **Code checks it first** (`keys.check`) and refuses, with why:
   - a sum's right answer that is not its arithmetic ("48 + 35 is 83, so 78 cannot be its right answer");
   - a box of an equation, which its equation marks (ADR 0043);
   - a question only a person judges;
   - a whole-number key given anything but a whole number;
   - a True / Not true key given anything but a claim, which is stored in the paper's own words;
   - the key it already is.
4. **The change is a row of its own** (`key_correction`, append-only, with the key it replaced).
   - `engine legacy paper` puts it back after entering the file (`keys.reapply`), so the deploy that enters every
     paper again (ADR 0043) never undoes it.
   - The paper's file is not edited from the page.
5. **Every answer to the question is marked again with it**, and a mark a person decided is never overwritten.
   - What a person typed the reading of (`again.mark_again`, limited to the question): an answer not yet signed off
     changes in place; a signed-off one gets a new batch of evidence in the educator's name, the old batch kept
     (ADR 0044).
   - What no person typed (`again.by_new_key`): only a mark its reading gives by the key it replaced came from that
     key.
     - Signed off as the reader read it: marked by the new key, with a new batch of evidence.
     - Judged by a person as the old key marked it: a judgement is never changed by the engine (ADR 0044), so it
       stays. Where the new key marks its reading otherwise, the educator is told how many such answers there are, to
       judge again.
     - Any other mark is a person's own call, which no key decided: a judgement against the old key, or a mark set
       before U3, when a paper's Right / Wrong / Blank signed it off and left no row. It stays, and the change says
       nothing about it.
   - What the reader read and no person has seen is marked as the reader's reading always is (`again.remark`,
     ADR 0029).
   - The page says how many answers changed, and how many keep a mark the new key disagrees with.
6. **Marking again after a deploy is unchanged: only what a person typed** (ADR 0044). A signed-off answer nobody typed
   is marked again only by a key change, as in 5. That code moved from `marking.py` (at its 400-line ceiling) to
   `w3_read/again.py`: marking an answer, and marking every answer again when its rule or key changes, are two jobs.

## Found on the way, fixed at the cause

The paper page asked `GET /capture/{id}/mistakes` with the paper's id (a `sheet_instance`), but `naming.unnamed` looked
answers up by the capture's id. It found none on the page, so Jev's shortlist for a wrong answer no named mistake
explains never showed on a paper page. Both lookups now take either id (`naming.ONE_PAPER`).

`deploy engine` and `migrate live` both start on a merge to main, and nothing ordered them. This merge's papers step
reads `key_correction`, which its own migration makes, so a deploy that got there first would fail, and an engine
restarted before the migration would fail every paper page. `deploy engine` now waits first: when the merge carries a
migration (the merge's own changed files, from the compare API), it waits for `migrate live` to succeed on the same
commit, up to ten minutes, and stops if it fails.

## Rejected

- **Editing the key in the paper's file from the page.** The file lives in the repository; a page cannot commit to it.
  A row the loader puts back does the same job and keeps who changed what.
- **Editing the `item` row alone.** The next deploy enters the file again and would silently undo the change.
- **Letting any key be typed.** 4A's 78 is exactly the change that looks right on one paper and marks every other
  child wrong. Code refuses what it can prove wrong, and shows the stored key everywhere, so a person sees the mismatch
  before reaching for the change at all.
- **Marking every signed-off answer again by the reading the engine stored** (the first build, 2026-09-30, caught
  before merge). Before U3, a paper's Right / Wrong / Blank left no row, so a person's Right on a misread 18 looks
  exactly like the engine's own mark. Marked again by its reading, the new key would make it wrong: a person's call
  overwritten with nothing to show for it. Only a mark its reading explains by the old key came from the key.
- **Changing a judgement that followed the old key.** It would make such an answer right at once, but the judgement row
  would still say a person judged it Wrong while the mark said right. The engine never changes a judgement
  (ADR 0044). It names these answers instead, and a person judges them again.
- **Naming each box on the card instead of showing its key** (the first idea, 2026-09-30). Nimish's ask covers it:
  once "Right answer: 83" sits beside "48 + 35 =", the box is plain.
