# 0096 — A kind of question is stopped, never deleted

Goal: goals/gen_retire_a_kind.yaml

Nimish, 26 Oct 2026: "the educator also, today, does not want certain types of questions. They should be able to delete
those kinds of questions from the bank itself."

## Decided

- **"Delete from the bank" is a stop.** An educator who may change the skill stops a kind at one level, or at every level
  that asks it. It is a row of `skill_level_kind_stop`, which the database refuses to change; a restart is another row,
  and the newest says where the kind stands (`kind_stopped`). `drawable_item`, the one view every paper draws from, leaves
  a stopped kind out at that level. Every question keeps its row and status, every past paper its questions, every answer
  its meaning (rule 4).
- **The educator reads what it touches first.** The engine counts the questions in the bank, the past papers holding them,
  and the papers approved but not yet given (this week's or later, no word that they were given, nothing read from them);
  the page says them before the educator confirms.
- **An approved paper not yet given goes back for approval, unchanged.** Its approval is cleared and its code is kept on
  the stop's row. The educator approves it again or makes a new one; nothing changes the paper silently.
- **The level's approval is withdrawn**, as any edit of a level does (`english_edit.withdraw`), for a stop and a restart.
  Until it is approved again the level is not confirmed, so no new paper draws from it at all; the confirm step says so.
- **A level keeps one kind in use.** A stop that would leave a level drawing nothing is refused in words.

## Rejected

- *Deleting the questions, or setting their status to retired.* A question with answers against it must stay readable,
  and a retired question cannot come back as it was: the kind is the educator's choice, not a fault in the question.
- *One row for a whole skill (no level).* Two rows could then disagree (stopped across the skill, started at a level);
  a stop across a skill is a row per level instead, and every reader asks one question: is this level's kind stopped?
- *Changing an approved paper to drop the stopped questions.* A paper approved by a person is never changed without them.
