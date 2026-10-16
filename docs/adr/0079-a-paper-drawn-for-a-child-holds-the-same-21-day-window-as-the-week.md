# ADR 0079 — A paper drawn for a child holds the same 21-day window as the week

**Status:** accepted (2026-10-16).
Goal: goals/l5-seen-means-the-last-21-days.yaml

## What happened

Neha, Grade 1's educator, asked the maker on live for one Class assessment for her 13 children: Equal groups
(repeated addition), Medium, 12 questions, one paper for all. It refused: "only 4 questions none of these 13 children
has been given in Equal groups (repeated addition) at Medium; ask for 4 or fewer".

Medium Equal groups is four or five groups of 2 to 6, as a sum or as a picture. At most 20 questions can exist, and the
bank holds 16 (`min_items`). ADR 0011 allowed a level to hold fewer than fifty questions because of the 21-day window:
"with a 21-day exposure window and 16 children, that property still holds comfortably". SPEC says the same ("across
weeks, exclude any item that child has seen in the last 21 days"), and the window is a threshold row, `exposure.days`.
The week's assembly reads it. `focus_paper._draw` draws every maker paper and every home assessment, and it refused
any question a child had *ever* been given. A level of 16 questions ran dry for a class for good, after a few papers.

## Decision

Every paper drawn for a child holds the one window: no question a child was given in the last `exposure.days` days.
A question given longer ago may come back. `settings.exposure_days` is the window's one reader. The week's assembly, the
maker, home assessments and the week's scenario check all read it there. When a line cannot be filled, the refusal
says the window it counted: "only 4 questions in Equal groups (repeated addition) at Medium that none of these 13
children has been given in the last 21 days; ask for 4 or fewer".

## Rejected

- **Widen Grade 1's Medium range** (groups of 2 to 10, say) so that more questions exist. That redefines what the level
  teaches. It is the school's decision, not one to take for a number (ADR 0011 rejected the same for R1 and R2). The
  ranges are already on the list Achal is confirming.
- **Make a picture's objects part of a question's identity**, so that dots, apples and stars count as three questions.
  The child would meet the same sum three times while the bank counted it as new.
- **Let only "one paper for all" repeat a question.** Then one rule would have two meanings, and a home assessment would
  still run dry for good.
- **Keep "ever" and tell the educator to choose another level.** The refusal would then be permanent, and on a level as
  small as Grade 1's it would come in the first month.

## Consequences

If the class was given so many of the level's questions in the last 21 days that fewer than 12 are left, a paper of 12
is still refused, and the refusal now says so. A second line at another level, or fewer questions, fills it.
