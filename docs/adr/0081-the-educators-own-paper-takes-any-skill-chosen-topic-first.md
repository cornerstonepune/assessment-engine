# ADR 0081 — An educator's own paper takes any skill, chosen topic first

**Status:** accepted (2026-10-16). Supersedes, for a paper an educator builds, F1e's "offers a class only those levels
… and the engine refuses any other" and F1f's "a skill whose topic the class has not been taught is refused".
Goal: goals/l7-a-line-is-topic-skill-level-number.yaml

## What happened

Achal called Nimish while an educator waited to make a Grade 3 Class assessment: 2-digit × 2-digit was not in the
maker, and neither were multiples and factors. Choosing Multiplication in the Topic box still left every skill in each
line's list. He asked for each line to be a topic, then its skills, then the level, then how many, with questions from
several topics on one paper.

Two rules hid the skills. The maker listed only the skills switched on as taught for the class (F1f), and only levels
of the class's grade or below (F1e). 2-digit × 2-digit is Grade 4 at every level, so a Grade 3 class never saw it.
Multiples and factors is not switched on in the school's rows. `focus_paper._asked` refused the same two things. The
Topic box filled the lines from a topic, but each line's list held every skill of every topic.

## Decision

Nimish chose, of three: "her choice decides".

- Each line of Make papers, and of a paper for one child, is a topic, then one of its skills, then its level, then how
  many questions. A paper can take its lines from different topics. The Topic box above the lines, renamed "Start from
  a topic", fills them as it did, and each filled line sits under that topic.
- Every skill of every topic is offered. Those the class's grade uses come first. A skill none of whose levels the
  class's grade uses says its grade ("· Grade 4"). A skill the class was not taught says "· not taught yet". A level
  above the class's grade says its grade. A skill's first level of the class's grade is chosen for it, Medium where
  it has one.
- The engine makes what the educator asked for: `focus_paper._asked` checks only that the skill set exists and has
  the level (`shelf.catalog(every=True)`).
- What the engine chooses by itself keeps both rules. That is a child's own next step (`home_area`, which reads the
  class's own `catalog`), the week's pack, and the change offered for one child's own next step on the maker.

## Rejected

- **Keep the grade limit and drop only "taught".** 2-digit × 2-digit would still be hidden from Grade 3. That was the
  first thing Achal asked for.
- **Keep both limits and only regroup the list by topic.** The skills he named would stay out of sight. The workaround
  (switch the topic on as taught in Curriculum) changes what the engine gives every child of the class, not this paper.
- **Filter each line by the Topic box above the lines.** That still allows one topic per paper, and he asked for
  several.

## Consequences

An educator can set a Grade 3 class a Grade 4 paper. The line says so before she sees the papers. A child's answers on
it count as evidence on that skill like any other. Nimish's 2026-10-14 sentence for F1e ("it's only easy and medium that
should come") now holds as an order rather than a filter: a Grade 2 class's own levels come first and are chosen by
default, and the higher ones are labelled.
