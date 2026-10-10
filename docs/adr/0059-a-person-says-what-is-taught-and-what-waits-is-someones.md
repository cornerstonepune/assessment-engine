# ADR 0059 — A person says what is taught, and what waits on a person is someone's

**Status:** accepted (2026-10-10, slice NY1 of BUILD-ORDER "NY1 and NY2").
Goal: goals/ny1-needs-you.yaml

## What happened

Nimish, 2026-10-10: *"I'm not even now able to figure out what all papers I need to validate or for Achal to
validate … I'm not seeing any of the multiplication, division."* Measured the same day (STATE.md "NY — measured before
the build"):

- **"Taught" was the rows' alone.** Nothing on the site switched a topic on. `engine load` copied `taught` from
  `topics.json` every time, so even a change in the database was undone by the next load.
  - "Untaught until an educator says so" (ADR 0047, A7) had no place for an educator to say it.
  - The eleven skill sets of the six topics left off — all multiplication and division beyond Grade 1's equal groups,
    and Reasoning — were on no screen.
- **They could not be approved either.** The approval page and Today read only taught topics, so these skills could
  be neither switched on nor approved.
- **Nothing was anyone's.** Every count on Today was the school's. The signed-in person's role was loaded and read
  nowhere, and sign-in landed on Curriculum.
- **What Achal is asked was not on the site.** It sat in a shared doc, the taxonomy's twelve assumptions, eight goal
  files and their pull requests.

## Decision

1. **Whether a topic is taught is a person's word.**
   - An educator switches a topic on or off on Curriculum, in their own name (`topic.taught_by`, `taught_at`).
   - The rows decide a topic only until a person has; a load never switches back what a person switched.
   - A change made in the database with no name on it is no one's decision, and follows the rows again.
   - Switched on, a topic's skills are on Curriculum, the Question bank and children's papers. Switched off, they keep
     their questions out of sight.
   - Switching off is folded away, so a stray click cannot hide a topic the school teaches.
2. **Approving a skill and teaching it are two decisions.**
   - A skill is read and approved before its topic is switched on, on its own page and on the approval page, each
     saying it is not taught yet.
   - Today, Curriculum and the approval page count the same waiting skills, taught or not.
3. **Each kind of thing waiting on a person is someone's, by a row.**
   - `people.decides` maps each kind to roles on the staff list (`app.staff`). It is drafted from ARCHITECTURE.md's
     steps for Nimish to correct:
     - the specialist confirms the doubtful answers, signs off what was read and confirms home papers (N9, N11);
     - an educator approves the class papers that print (N7) and says what is taught;
     - the coordinator approves the skills.
   - Today shows the signed-in person's first ("For you"). The rest say whose they are by name, or that no one on the
     staff list has that role yet — a gap a person closes by adding someone.
   - A role says whose a thing is, not who may do it: anyone signed in still acts on anything.
4. **A question the engine drafts for a person is a row they answer on the site.**
   - `ask`, loaded from `supabase/seed/asks.json`: the taxonomy, its twelve assumptions, and each slice's decision
     drafted for Achal.
   - Each is held word for word to its source by a test (`tests/test_asks.py`), so a goal that drafts something for
     Achal fails until he can see it.
   - It is agreed as drafted, or corrected in the person's own words, in their name.
   - A load rewords a question no one has answered and never touches one answered.
   - `engine asks` prints every answer. `bin/update-live` runs it, and so does its rehearsal on a copy of live, so
     whoever builds next reads what was said.
5. **Sign-in lands on Today**, where what waits is.

## Rejected

- **Taught grade by grade.**
  - The agreed rule is that a topic is taught or not, as a whole (goals/v1-only-what-is-taught.yaml), and every paper
    is approved by a person before it prints.
  - A7's "until the grade declares it" is asked of Achal as a question of its own (`NY.TAUGHT_WHOLE_SCHOOL`) rather
    than built on a guess.
- **Roles as permissions.** A small school where one person is away would stop. The page says whose; it does not
  lock.
- **Copying Achal's drafts onto the site by hand.** A copy drifts. Each row is held to its source instead, as the
  website's mistake names are held to the engine's (`mistake_name`, migration 20261027090000).
- **The seed's `taught` as a one-time value** (`seed_once`, as `app.staff`). The topics' order and skills still come
  from the rows on every load; only the switch is a person's, and only once a person has used it.
