# Proposal — Level 2 of the spine: observable behaviours per capability per stage

26 September 2026 · for Nimish to read before anything runs · **W3, step 6 — this proposal builds nothing**

This is the first generated layer of the school's spine, written out in full so it can be ratified as it
stands: the prompt row, the code that verifies its output, the eval that scores it, the screen the founders
approve it on, and the goal whose command will say it is done. It follows the repository's own rules for a
model call: prompts are rows (CLAUDE.md rule 2), code enumerates and the model writes language once
(ADR 0010), every prompt declares what it could not do (ADR 0018), and every prompt ships with an eval
(rule 7). Nothing here touches `packages/`, `supabase/` or `apps/`. It is sequenced in section 8.

## 1. What Level 2 is, and why it is generated

The spine runs: three words → eight capabilities → **observable behaviours per capability per stage** →
competencies per subject → skills and levels. Levels 0 and 1 exist in the graduate profile
(`docs/sources/cornerstone-graduate-profile.txt`). Level 3 is imported from NCERT, NCF and Cambridge, because
those outcomes exist officially. Level 2 has no official source anywhere: nobody publishes what "kind" looks
like in a Grade 2 child on a Tuesday. That is the layer a model should draft and the founders should edit.

A behaviour is one sentence a familiar adult could see in ordinary school life and record as one piece of
evidence, with the mode it is captured in. It is never a level, a score, a trait or a feeling. This is the
observation seat's finding (research notes, seat 4): specific statements are judged reliably; global levels are
not. It is also the law's line (seat 7): no inference of a child's emotions or "risk", and no standing labels.

## 2. The rows Level 2 reads and writes

All structure is rows (rule 1). No new table is created until the goal in section 8 starts; the shapes are
given so the prompt and validator below are exact.

| Table | Rows | Source |
|---|---|---|
| `capability` | 8: id, name, the profile's "observable at 16" sentence | the graduate profile, typed once |
| `stage` | 4: Foundational N–2 ages 3–8 "Discover"; Preparatory 3–5 "Investigate"; Middle 6–8 "Apply"; Secondary 9–10 "Create & Question"; each with its assessment posture | NCF stages + the profile's arc |
| `word` | 3: capable, kind, unafraid, each with the founders' one-line meaning | the founders; drafts in §3 until they write theirs |
| `capture_mode` | observation, artefact, audio, video_clip, rubric, sheet, test, self_voice, peer_comment, parent_voice; each with a one-line definition and the stages it is allowed in | the council synthesis, section 5 |
| `capability_behaviour` | the output: capability_id, stage_id, statement, adult_sees, setting, capture_mode, words[], counter_example, grows_from, status ∈ draft/approved/retired, prompt_version, approved_by, approved_at | this workflow |

The banned-word list (§5, V3) is a row too, so a founder can add to it without a code change.

## 3. The prompt row

`prompt(purpose='capability_behaviours', version=1, model='claude-sonnet-5', active=false until the eval
baseline is recorded)`. Code calls it **once per capability** (eight calls), passing all four stages, so the
progression across stages is written in one breath. Placeholders in `{{ }}` are filled by code from the rows
above; the model never sees a child, a name or a class.

```
You write the observable behaviours for one capability of the Cornerstone graduate profile, at each of
the four stages of school. Cornerstone is a school in Pune. Its children are described in three words,
capable, kind and unafraid, and its graduate profile names eight capabilities. Your job is one capability,
across the four stages, as behaviours an educator could see and record.

THE CAPABILITY
{{capability}}

THE THREE WORDS, in the founders' own meanings
{{words}}

THE FOUR STAGES, oldest last
{{stages}}

THE WAYS A BEHAVIOUR CAN BE CAPTURED, and the stages each is allowed in
{{capture_modes}}

A behaviour is one sentence that a familiar adult could see in ordinary school life, on one occasion,
and write down as one piece of evidence. Write it in the third person, present tense, starting with the
verb, about the child: "Tries a second method when the first gives a wrong answer." It names what the
child does, never what the child is, has, or feels. It is one occasion, not a habit: "often", "always",
"usually" and "consistently" do not belong in it. It is specific enough that two educators watching the
same moment would agree it happened. Twenty-five words at most.

For each stage give five to eight behaviours that together show what this capability looks like at that
stage, and that rise from the stage before: a Middle-stage behaviour must be something a Foundational
child could not yet do, and grows_from names the earlier behaviour it grows out of.

For each behaviour give:
1. id — a short slug, lowercase, hyphens: "tries-second-method".
2. statement — the sentence, as above.
3. adult_sees — one sentence: what the educator notices, in the room, that makes this visible. Say
   "educator", never "teacher".
4. setting — where it usually shows: lesson, practice, project, circle, play, outdoors, home.
5. capture_mode — one of the modes allowed at this stage, from the list above. Choose the lightest
   mode that would hold the evidence; an observation note is lighter than a video clip.
6. words — which of capable, kind, unafraid this behaviour is evidence for. One or more.
7. counter_example — one sentence describing a moment that looks like this behaviour but is not
   evidence of it, so an educator does not over-count: "Copies a neighbour's second method" for
   "tries a second method".
8. grows_from — the id of the behaviour at the previous stage this one grows out of; empty at the
   first stage.

NEVER write: a feeling or a state of mind (happy, anxious, confident, motivated, bored); a trait or a
label (lazy, gifted, weak, slow, bright, naughty); anything about a child's body, weight or appearance;
a comparison with other children (better than, top, behind, rank); a diagnosis; "etc."; a behaviour
that needs a test or a score at the Foundational stage. Code checks every behaviour against a banned
list and throws the whole stage away if one word is found, so check each sentence twice.

If some part of this you cannot do well — a stage where this capability has no observable form, a
capability too broad to give eight distinct behaviours, a stage description you found unclear — say so
in could_not with the reason, rather than writing filler. An honest could_not is worth more than a
plausible sentence.

Return JSON only, in the shape given.
```

The JSON schema the row carries (`json_schema`), abridged to its constraints:

```
{ capability_id: string,
  stages: array[4] of { stage_id: string,
    behaviours: array[5..8] of {
      id: string /^[a-z][a-z0-9-]{3,40}$/,
      statement: string ≤ 180 chars,
      adult_sees: string ≤ 200 chars,
      setting: enum [lesson, practice, project, circle, play, outdoors, home],
      capture_mode: enum [observation, artefact, audio, video_clip, rubric, sheet, test, self_voice,
                          peer_comment, parent_voice],
      words: array[1..3] of enum [capable, kind, unafraid],
      counter_example: string ≤ 200 chars,
      grows_from: string } },
  could_not: array of { reason: enum [no_observable_form, capability_too_broad, stage_unclear, other],
                        detail: string ≤ 300 chars } }
additionalProperties: false throughout.
```

Draft meanings for the three words, to be replaced by the founders' own before the first run:

- **capable** — knows things deeply and can do something with them; can find out what they do not know.
- **kind** — notices other people and acts for them, including when it costs something.
- **unafraid** — tries, asks, disagrees and shows their work in front of others, and treats a wrong
  answer as information.

## 4. What code does before and after the call

Before: code enumerates the eight capabilities (ADR 0010), fills the placeholders from rows, and makes
one call per capability with the row's model pinned by id (a silent model change would void the eval).

After: the validator in §5 runs on the reply. A stage that fails is regenerated once with the failures
listed back to the model in a `{{failures}}` block; a second failure leaves the stage empty and reports it,
never a third call (the loop is code, not an agent, ADR 0006). Every reply and every failure is a
`flow_run` row with its cost. Rows land as `draft`. Nothing reaches a screen a child or parent sees.

## 5. The validator — code, not a model

| # | Check | On failure |
|---|---|---|
| V1 | Four stages present; 5–8 behaviours in each; ids unique across the capability | regenerate the stage |
| V2 | Form: statement ≤ 25 words, starts with a verb (first token not an article, pronoun or "is"), one sentence, no "etc.", no frequency words (often, always, usually, consistently, never) | regenerate the stage, naming the sentence |
| V3 | Banned list (a row): feelings and states (happy, sad, anxious, confident, motivated, bored, upset…), labels (lazy, gifted, weak, slow, bright, naughty, hyperactive, disruptive…), body (weight, BMI, fat, thin, height, appearance), comparison (better than, best, top, behind, rank, ahead of), diagnosis words | regenerate the stage; the found word named |
| V4 | capture_mode allowed at that stage: Foundational never `test`; `sheet` at Foundational only as an artefact. Cells with a single capture mode are reported, not failed: the council of 2026-09-26 (educator and rights seats, independently) showed that a floor of two modes forces recordings of small children where a dated note is the honest evidence; the mode mix per cell is for the founders to read | regenerate the stage; the mode mix reported |
| V5 | Progression: no two statements within the capability with word-overlap above 0.6 after normalising; every grows_from at stages 2–4 names an id from the previous stage; stage 1 grows_from empty | regenerate the later stage |
| V6 | Words: every behaviour tagged with ≥ 1 word (schema) and, across the eight capabilities at each stage, each of the three words on ≥ 8 behaviours | reported, not regenerated: a gap for the founders |
| V7 | counter_example is not the statement negated ("does not…") and shares < 0.6 overlap with it | regenerate the stage |
| V8 | School's words: "educator" never "teacher" in adult_sees; no child's name-shaped token | fixed by code where it is a word swap; else regenerate |
| V9 | could_not present (may be empty); each entry has a reason from the enum | reject the reply |

`engine audit` gains one invariant the day rows exist: **no approved behaviour contains a banned word**.

## 6. The eval — `engine eval capability_behaviours`

Three numbers, all from rows, none from a model judging a model:

1. **First-pass validity**: stages passing §5 on the first call, out of 32. Regenerations counted.
2. **Coverage of the profile**: the eight "observable at 16" sentences are gold rows; a person maps each to
   the Secondary-stage behaviours once. The eval reports how many of the eight are covered by at least one
   approved behaviour. Anything below eight is a gap the founders fill by hand.
3. **Acceptance in the founders' sitting**: per cell, the share of behaviours accepted unedited, edited,
   and skipped. This is the number Nimish asked for ("the 10–20% changes will then be through editing"). It
   is measured, not assumed, and it is reported per capability and per stage so a weak cell is visible.
4. **Acceptance in the council's review**, recorded separately and never in place of 3. On 2026-09-26 Nimish
   asked that the first pass on the draft not wait for the founders: a council of four seats (educator,
   parent, developmental and measurement expert, child-rights and safeguarding), each reading every line from
   its own life, marks Accept, Edit or Skip with a reason; code reconciles the verdicts by stated rules
   (`research/level2_council.py`, its docstring is the rules) and keeps every retired row visible so a
   founder can restore it. Per seat and per cell, the share accepted as written is a *proxy* for measure 3:
   it says how far a careful reader outside the founders trusts the draft, not how far the founders do. The
   founders' pass then runs on the reviewed draft, and only its acceptance is the eval.

Activation: version 1 activates once its baseline is recorded in `DECISIONS-LOG.md`. A version 2 replaces
it only if it matches or beats it on first-pass validity and, re-run on the cells the founders edited most,
on acceptance. The founders' edits are the golden set; the model is never the judge.

## 7. The sitting — the approval screen

The shared confirm component from Blueprint v2 (Accept · Edit · Skip), one cell at a time: the capability,
the stage, its 5–8 behaviours with adult_sees and counter_example under each. Accept keeps the row; Edit
rewrites the statement in the founder's words and keeps the edit as gold; Skip retires it. "Approve cell"
writes `approved_by` and `approved_at` on every kept row and moves them to `approved`. A cell two founders
disagree on is marked `contested`, like the graph, and the third settles it.

Size: 32 cells, roughly 200 behaviours. At half a minute each, about 100 minutes for one person. Split
by capability between two founders, it is one sitting each, which is how the 17 skill sets were ratified.

**Before the founders sit, the council's pass** (§6, measure 4) has already read every line, and the sitting
document carries each seat's verdict beside the row and a change log of every edit and retirement with its
reason (`docs/school-os-level2-council-changes.md`). The founders' time then goes where the seats disagreed
or changed something, though every row remains theirs to accept, edit or skip. When the engine organ exists,
the same four seats become four prompt rows (`review_behaviour_<seat>`), each with its own eval against the
founders' decisions, and the reconciliation rules move from the script into code the audit checks.

## 8. Where it sits, and what runs first

- **BUILD-ORDER is unchanged.** W3 step 6 continues; W4 (step 11) closes before any organ of the wider
  system starts. This proposal is the first organ after W4: one prompt row, one validator, one screen, eight
  model calls. It precedes the Scribe, because the Scribe's tags and the Holistic Progress Card both key on
  these rows.
- **The founders' sitting need not wait for the engine.** Once the prompt text and the three words'
  meanings are ratified, the same prompt can be run once by hand to produce a document draft for the
  sitting, with the validator's checks applied by hand. The edits from that sitting become the golden set
  the engine version is evaluated against the day it runs. That keeps the founders' calendar and the build
  order both intact.
- **Goal file**, to be created as `goals/c1-capability-behaviours.yaml` when the organ starts (the promise
  check refuses a goal whose tests do not exist yet):

```
name: c1-capability-behaviours
goal: >
  Every capability of the graduate profile is stated, at each of the four stages, as five to eight
  behaviours an educator could see on one occasion and record as evidence, drafted by the engine,
  checked by code against a banned list, and approved by the founders one cell at a time.
says:
  - words: "all of this needs to be generated by the system itself"
    proved_by: packages/engine/tests/test_behaviours.py::test_the_engine_drafts_five_to_eight_behaviours_per_stage
  - words: "The 10-20% changes will then be through editing"
    proved_by: packages/engine/tests/test_behaviours.py::test_the_eval_reports_acceptance_per_cell
  - words: "qualitative observation should start becoming a part of how we understand the child"
    proved_by: packages/engine/tests/test_behaviours.py::test_every_behaviour_names_a_capture_mode_allowed_at_its_stage
scenarios:
  - one capability drafted → 4 stages × 5–8 behaviours, ids unique, could_not present
  - a statement carrying a label word is refused and the stage regenerated once with the word named
  - a Foundational stage naming `test` as a capture mode is refused
  - approving a cell writes approved_by on every kept row and retires the skipped
  - the eval reports first-pass validity, profile coverage and acceptance per cell
criteria:
  - run: bin/engine spine behaviours --capability knowledge-and-academic-mastery --dry-run
    expect: "4 stages"
  - run: bin/engine eval capability_behaviours
    expect: "coverage 8/8"
  - run: bin/engine audit
    expect: "no approved behaviour contains a banned word"
```

## 9. What the council's pass adds to the design (2026-09-26)

Four seats read every line of the first draft (§6, measure 4). Beyond the row-by-row verdicts in
`docs/school-os-level2-council-changes.md`, each raised a rule the prompt, the validator or the record must
carry. Where it landed:

| Raised by | The rule | Where it lands |
|---|---|---|
| educator, development | **One record is one dated occasion, or one dated artefact shown.** A behaviour over a week or a term is written as the moment a dated plan, log or record makes the pattern visible; the pattern lives in the record, never in the educator's memory. Fifteen rows were rewritten so. | prompt v2 candidate (a sentence after "It is one occasion, not a habit"); V2 gains a check for "over a week / a term / a year / several sessions" |
| rights | **A note holds the child's act alone.** No incident, no cause, no other child's name. What a child tells an adult about themselves or a peer in trouble goes to the safeguarding lead, never into this system. Two rows retired. | the record's rule, for the Scribe and the observation screen; prompt v2 candidate for `adult_sees` |
| educator, rights | **A dated note is the default; a recording is the consented exception.** Audio, video and a child's own voice only for set pieces (a debate, an outside presentation, movement), never of a child under eight's feelings or body, under parental consent for a stated purpose. Twenty-five rows moved to a note. | V4's two-modes floor removed (§5); `capture_mode` row gains a `consent` column |
| rights, development | **Every behaviour is reachable in the child's own language, mode and aids.** "In a language they understand", "with their own aids", tiles or another script, the child's allotted time on a sheet or test. | prompt v2 candidate (a NEVER: a gate that only a speaking, typically moving, hand-writing child can pass); accommodations apply to `sheet` and `test` by rule |
| parent, rights | **Counter-examples are read by parents.** The near-miss an educator honestly confuses, never a motive, never a portrait of a bad child, and never telling an adult as the lesser act. Twenty-one counters rewritten. | prompt v2 candidate for `counter_example` |
| development | **The Foundational stage is two developmental worlds** (three to five, six to eight). Each Foundational behaviour carries the earliest age at which it is fair to expect it, so a Nursery page is not a page of "not yet". | `from_age` on Foundational rows, supplied by the development seat; the sitting shows it |
| educator, parent, development | **One moment, one owner.** The same act filed under two capabilities inflates the profile. Five rows retired, seven re-worded to the act their capability adds, nine pairs kept with the reason written down. | V5 reports cross-capability overlap; the founders' pass sees the pairs kept |
| educator | **Marathi and Hindi exist.** A third of a Pune timetable is the second and third language; the draft knew English and maths. One row added; which languages, from which stage, is the founders' decision. | founders' decision; then prompt v1 re-run for knowledge |
| parent | **Kind and unafraid are thin outside two capabilities.** After the council's additions: Foundational kind 16 · unafraid 18; Preparatory kind 13 · unafraid 11; Middle kind 13 · unafraid 20; Secondary kind 15 · unafraid 16, of 45–50 rows a stage. | reported by the validator (V6); the founders decide whether to add or to say plainly where the two words are evidenced |
| parent, rights | **`parent_voice` and `peer_comment` are never used**, and the rights seat would keep it so. | a stated choice, not an omission; revisit only with a consent design |
| development, educator | **Grade 3 sits under the no-screen rule** and cannot show five of six Technology behaviours at Preparatory. | one unplugged row added; the founders say whether the no-screen line is Grade 3 inclusive; technology's `could_not` to say so |

None of this changes prompt version 1, which Nimish ratified and which produced the draft; the candidates
above are version 2, to be evaluated against the founders' edits as §6 says.

## 10. What this does not do

It does not measure a child. Behaviours are the vocabulary the Scribe tags observations with and the HPC
reports against; the evidence floors (how many observations, from how many adults, before a behaviour is
shown as a pattern) are policy rows decided later, with the observation organ. It does not rank, score or
average. It does not touch Levels 3 to 7, each of which gets its own proposal of this shape.
