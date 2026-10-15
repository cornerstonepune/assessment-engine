# ADR 0076 — Topics are operations; a class is taught skill by skill

**Status:** accepted (2026-10-15).
Goal: goals/t1-topics-are-operations.yaml

## What happened

On 2026-10-15 Nimish looked at live's Children page and saw these topic chips: Addition & subtraction, Reasoning, Number
sense & strategies, Estimation, Multiplication, Multiplication models, Word problems, Multiplication facts and place
value, Multiplication in columns, Data handling. He said: "You are putting estimation word problems as a potential
topic. How can that be a topic? These are types of problems. The topics are core addition, subtraction,
multiplication, division, and factors."

Measured the same day:

- **Three of the chips are dead rows.** "Number sense & strategies", "Estimation" and "Word problems" left
  `topics.json` on 2026-09-23 (#44), when their skills moved into Addition & subtraction. `engine load` updates a
  topic it is given and places every skill, but never removes a topic the seed no longer has. So the rows stayed on
  live, empty but still switched on, and the Children page lists every topic that is switched on.
- **The seed's own list is 16 topics.** Nine of them are slices of × and ÷ from the M&D taxonomy: models, facts and
  place value, columns, mental, estimating, equations, multiples, stories. Estimating, stories, equations and mental
  methods are kinds of question a skill asks, not topics.
- **The topic is also the "taught" switch** (goals/f1f-taught-per-class.yaml, `class_topic`, `taught_in`). Folding
  "Multiplication in columns" into "Multiplication" with one switch would put column multiplication on a Grade 3
  class's papers the day Multiplication was switched on for it, taught or not.
- **On a copy of live, Multiplication is already switched on for G2 and G3.** So MUL.FACTS, MUL.MODELS and MUL.2D1D,
  and from SF1 also MUL.THREE and MUL.NTH, are on their papers.

## Decision (Nimish, 2026-10-15, from the options put to him)

1. **Six topics, by operation:**

   | Topic | Skills |
   |---|---|
   | Addition & subtraction | every `ADD.*` and `SUB.*`; estimation, missing digit, inverse, efficient strategy, the add/sub stories; judging a claim (REASON.EXPLAIN) |
   | Multiplication | groups, models, facts, tens, three numbers, columns |
   | Division | groups, facts, tens, by a 1-digit number; and the skills that mix × and ÷ (mental, estimating, equations, stories), which can only be taught once division is |
   | Multiples & factors | multiples and factors; the nth multiple |
   | Number sense | sequences (place value when it comes) |
   | Data handling | tally |

   Addition and subtraction stay one topic: missing digit, inverse operations and the stories use both, and would have
   no home if they were split.
2. **A class is taught skill by skill.** Switching a topic on for a class switches on all its skills. An educator can
   then leave one skill off, for example column multiplication until next term. A topic shows as taught in a class
   when any of its skills is taught there. The one rule stays in the database (`skill_taught_in`), read alike by the
   engine and the site.
3. **Nothing on a paper changes on the day.** The migration writes down every active class's word on every skill, as
   the old topics give it, before any skill moves topic. So a class keeps exactly the skills it had, whichever topic
   they now sit in.
4. **A topic the seed no longer has is removed on load,** with its classes' words. A skill in no topic is still
   refused, as before.

## Rejected

- **Exactly five topics: addition, subtraction, multiplication, division, factors.** Data handling and number
  sequences would have to sit inside an operation, and the skills that use both + and − would have no home.
- **The switch stays per topic.** Simpler, but one switch would put every multiplication skill of a grade on its
  papers at once.
- **Hiding empty topics on the site only.** That would treat the symptom. The dead rows would still be switched on and
  still be counted.
