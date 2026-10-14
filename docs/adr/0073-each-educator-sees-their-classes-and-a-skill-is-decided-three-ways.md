# ADR 0073 — Each educator sees their own classes, and a skill is decided three ways

**Status:** accepted (2026-10-14, phase 1 of BUILD-ORDER "One flow for the educator").
Supersedes the "no more layers" line of goals/ui4a-staff-and-search.yaml (2026-10-11).
Goal: goals/f1a-each-educator-has-classes.yaml

## What happened

Nimish, 2026-10-14, after using the site with the educators: *"While the teachers are now starting to use it, the flow
does not feel coherent … create a mapping of the teacher to the grade … Then the teachers only see, when Achal logs in,
things that are relevant to his grades."* And on Curriculum: *"When I approve a skill, it gets approved throughout all the
grades. If I just want to approve something for a grade level today, I'm not able to do that … for grade two … it's only
easy and medium that should come."*

Measured the same day, from the code (the coherence list, claude.ai/artifact/B8kEMSmobq3pbWiJCVEDF8):

- **A person has no classes.** The staff list (`config.app.staff`, ADR 0069) holds an email, a name, a role and a
  password hash. Every page lists every class; `lib/needs-you.ts` says it outright: "Every line is shown to everyone".
- **The role is read in two places only**: the "How it works" link, and the order of the open questions. Anyone signed in
  may approve a skill, approve a pack or sign off answers.
- **"Approve" is one flag per skill set** (`skill_set.status`), for every grade and every level, and nothing that makes a
  paper reads it: only the audit and Today's count do. Changing any of seven columns, a word included, sends the whole
  skill back to draft.
- **Which levels a grade uses** is one grade per level (`skill_set.level_band`), read as "this grade or below" by the
  home paper and ignored by Make papers when an educator picks the skill.
- **"Taught" is one switch per topic for the school** (`topic.taught`): switching multiplication on for Grade 3 switches
  it on for Grade 1.

## Decision

Nimish took each recommendation of the coherence list ("go with your recommendations, start phase 1"):

1. **D1. An educator is linked to classes; the grade follows from the class.** Each person on the staff list names the
   classes they teach. The coordinator's classes are every class. A class is a `child.section` with a child in it.
2. **Every page opens on the signed-in person's classes.** The coordinator sees the school and can narrow it to a class.
   An educator linked to no class yet sees the school, with a line saying so, rather than an empty site.
3. **Who decides what is enforced, not only shown.** `people.decides` names the roles for each kind of decision; a server
   action checks it before it writes. The coordinator may take any decision. **D3:** educators draft skills; the
   coordinator (Aseem) approves them, as workflow N1 agreed on 16 Sep.
4. **D2. A skill is decided three ways, each by its own owner:**
   - *These questions are right*: per skill × level, once, by the coordinator. A correct Easy question is correct for
     every grade, so it is not approved per grade. Changing a level's rule withdraws that level's approval only; changing
     its words withdraws none, since the questions did not change.
   - *This grade uses these levels*: the grade plan, a row per grade × skill × level.
   - *My class has been taught it*: **D5**, per class × topic, with who and when.
5. **A level whose questions are not approved goes on no paper.** This ships last and only after it is measured on a
   copy of live, so the levels it would close are named to Nimish before any educator meets a refusal.
6. **D6.** Marking gets its own menu item (phase 5).

## Rejected

- **A staff table with a staff–class table.** It is the shape a later decision may want: decisions signed by a person's
  id rather than their email. Today it would move sign-in mid-term for no gain. The classes live in each person's entry
  of the list ADR 0069 made the database's: one source, no row that can outlive its person.
- **Approving questions per grade**, as first asked. The same questions would be approved up to four times, and a grade's
  real decision — which levels it uses — would still have nowhere to live.
- **Scoping only by hiding.** A page that hides another class's papers but whose action accepts them is not scoped.
