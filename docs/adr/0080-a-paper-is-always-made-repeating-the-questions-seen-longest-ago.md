# ADR 0080 — A paper is always made, repeating the questions seen longest ago

**Status:** accepted (2026-10-16). Supersedes ADR 0079's "Consequences" (a short line was refused); its window stays.
Goal: goals/l6-a-paper-is-always-made.yaml

## What happened

ADR 0079 gave every drawer the 21-day window, but a line the window could not fill was still refused: "only 4 questions
… none of these 13 children has been given in the last 21 days; ask for 4 or fewer". The educator then had to choose
fewer questions, another level, or a second line. Nimish, the same morning: "I don't want teachers to have this many
complications. Can we just make it simplified". Of three ways he chose the first: always make the paper.

## Decision

Every drawer of a child's paper (the maker, a home assessment, the week's pack) takes, in this order:

1. the questions none of the paper's children was given in the last `exposure.days` days, and no other paper of the
   batch holds;
2. then the questions those children were given longest ago, oldest first;
3. then the questions another paper of the batch holds.

A paper never holds one question twice. The paper says, in one quiet line, how many of its questions were seen before:
"5 of these questions were seen before: the bank had no more fresh ones." The week's pack gives a child who has sat
every worksheet at a level the one sat longest ago.

A paper is refused only when it asks for more questions than the level holds at all, and it then says how many the
level holds: "Equal groups (repeated addition) holds 16 questions at Medium; ask for 16 or fewer". A level with no
worksheet yet still names the child it could not give a paper to, with "run engine library build".

## Rejected

- **Fill from the neighbouring level.** The educator chose the level. A paper silently made easier or harder misstates
  what the child was assessed at, and the marks would land on the wrong level.
- **Keep the refusal, in plainer words.** The educator would still have to make a choice the system can make, and on
  Grade 1's small levels the refusal would come every few weeks.
- **Repeat at random.** A question seen yesterday is remembered; one seen a month ago much less. Oldest first is the
  least-remembered repeat.

## Consequences

A child can meet a question again inside 21 days when the bank at that level is small. The paper says so; nothing hides
it. The real fix for a small level is a bigger level, and that is the school's (Achal is confirming the ranges).
