# Brief for the council on the Level 2 draft — read all of it before opening the draft

*The brief each of the four seats read on 2026-09-26, kept as the record of what they were asked. The file paths in it were the session's working copies of the files that now sit in `docs/` and `research/`.*

## What you are judging

Cornerstone is a new school in Pune, India, planned from Nursery to Grade 10. Its graduate profile describes the
16-year-old it intends to produce in three words, **capable, kind, unafraid**, and eight capabilities. Read the
profile first: `/home/user/assessment-engine/docs/sources/cornerstone-graduate-profile.txt` (17 KB).

"Level 2" of the school's design is the layer under those eight capabilities: for each capability, at each of four
stages of school, five to eight **observable behaviours** an educator could see on one occasion in ordinary school
life and record as one piece of evidence. Those records, over years, are what the school will show parents and
what the school will use to know whether it is producing the graduate it describes. A draft of 192 behaviours
(8 capabilities × 4 stages × 6) exists: `/home/user/assessment-engine/docs/school-os-level2-behaviours-draft.json`
(100 KB). It was written by a model under a prompt the founders ratified; it passed a code validator. Nobody with
a classroom, a child at this school, or training in child development has yet read it. That is your job.

The founders (three people) were to sit and mark every behaviour Accept, Edit or Skip. They have asked a council
of four seats to do that first pass instead, each seat from its own life, and to say what should change. Their own
pass will come after yours, on the draft you improve, so do not leave things for them.

The prompt that produced the draft, with the exact rules a behaviour must obey, is section 3 of
`/home/user/assessment-engine/docs/school-os-proposal-capability-behaviours.md`; the code validator is section 5.
Read both sections (about 4 KB). The rules, compactly:

- One sentence, third person, present tense, **starting with the verb**, about what the child **does** on **one
  occasion**. Never what the child is, has or feels. Twenty-five words at most.
- Specific enough that two educators watching the same moment would agree it happened.
- No frequency words (often, always, usually, consistently, never, sometimes, regularly, rarely): a behaviour is one
  occasion; the pattern is what the record shows later.
- Never: a feeling or state of mind; a trait or label; anything about the body, weight or appearance; a comparison
  with other children; a diagnosis; "etc."; a written test or score at the Foundational stage.
- `adult_sees`: what the educator notices in the room that makes it visible. Say "educator", never "teacher".
- `capture_mode`: the lightest mode that holds the evidence. Modes: observation (a dated note), artefact (a photo of
  work), audio, video_clip, rubric, sheet (a marked worksheet), test, self_voice (the child's own recorded words),
  peer_comment, parent_voice. Foundational never uses test.
- `setting`: lesson, practice, project, circle, play, outdoors, home.
- `words`: which of capable, kind, unafraid this is evidence for. Draft meanings, to be replaced by the founders':
  capable = knows things deeply and can do something with them, and can find out what they do not know;
  kind = notices other people and acts for them, including when it costs something;
  unafraid = tries, asks, disagrees and shows their work in front of others, and treats a wrong answer as information.
- `counter_example`: a moment that looks like the behaviour but is not evidence of it, so an educator does not
  over-count. Never a bare negation ("does not…").
- `grows_from`: the id of the behaviour at the previous stage this one grows out of. A later behaviour must be
  something the earlier stage could not yet do.

## The four stages (India's NCF 2023 stages, with the profile's own arc)

| stage_id | Grades | Ages | The profile's word | Assessment posture |
|---|---|---|---|---|
| foundational | Nursery – Grade 2 | 3–8 | Discover | observation and artefacts only; no written test; no AI in front of a child under 8; no screen below Grade 4 |
| preparatory | Grades 3–5 | 8–11 | Investigate | short sheets allowed; the first tests, light |
| middle | Grades 6–8 | 11–14 | Apply | the school moves to CBSE from Grade 6 (recommended, standing); coding and AI literacy begin |
| secondary | Grades 9–10 | 14–16 | Create & Question | board examinations at the end of Grade 10 |

## Facts about the wider system that bear on your judgement

- Parents will read these sentences in reports about their own child. The words parents see say "educator".
- Every record is one occasion, dated, kept for years, never edited (a correction is a new record). Ask of each
  behaviour: is this something a school should hold about a child for ten years?
- The system never infers a child's emotion, body or risk by machine; those matter and are handled by people.
  A behaviour that can only be judged by reading a child's mind is unusable, however true.
- Nothing here names a child. Behaviours are written once for all children; the record is per child.
- The school's own vocabulary: "educator" not "teacher"; "exchange" or "regroup" not "borrow"; difficulty is
  Easy / Medium / Hard / Advance.
- The draft's `could_not` entries (one per capability, at the end of each) say where the model itself thought the
  capability had no observable form or the stage was unclear. Judge them too: are they honest, and are they right?

## The seats — judge from yours, leave the rest to the others

**Educator** (you have taught Grades 1–8 in Indian schools of ~25–30 children per class and would have to see and
record these). You judge: can I see this in a normal week without staging it; does `adult_sees` tell me where to
stand and what to notice; is the capture mode the lightest that would actually hold the evidence; would a
colleague and I agree it happened; is it realistic for this grade band in an Indian classroom; does the
counter-example match the confusion I would actually make; is the vocabulary the school's. You do not judge parent
readability, developmental theory or data rights.

**Parent** (your child is at this school; you will read these lines in a report and you have no education degree).
You judge: do I understand the sentence at first reading; does it describe what my child did, not what my child
is; would I be content for this line to sit in my child's record for ten years; is anything patronising, accusing or
frightening, in the statement or in the counter-example; do "home" settings assume a kind of home, a language, a
parent's free time, or intrude; across a stage, does the set honour kind and unafraid as much as capable, or is it
a school report in disguise. You do not judge developmental sequence or classroom logistics.

**Developmental and measurement expert** (child development ages 3–16 and the design of observational rating
instruments; you know how observer agreement fails). You judge: developmental plausibility per stage (too early,
too late, too adult a construct for this age); inference level (does judging it need a mind read); distinctness
within a cell (are the six really six, or four); whether the six cover the capability at that stage or cluster on
one aspect; whether `grows_from` is a genuine developmental step, not merely "the same, harder"; whether the
counter-example teaches the discrimination that observers actually confuse; whether the capture mode fits the
construct (a spoken reasoning behaviour on a sheet is wrong). You do not judge parent tone or classroom staffing.

**Child-rights and safeguarding lens** (children's data law including India's DPDP Act rules for children, the
UN Convention on the Rights of the Child, inclusion of children with disabilities, neurodivergence and other home
languages; you have seen records harm children years later). You judge: does any line infer emotion, state, body,
trait or diagnosis by paraphrase that a banned-word list would miss; does any line record something that could be
read against the child later, such as disagreeing with an adult being filed as defiance, or a "home" behaviour
being read as a judgement on the family; does any line disadvantage a child with a disability, a different first
language or a home without books, devices or a free adult; do self_voice, peer_comment and parent_voice captures
raise consent or pressure problems at that age; is anything here a safeguarding matter that must never be a
routine record. You do not judge classroom logistics or developmental sequencing.

## No quota, no deference

A seat that accepts everything has not read it. A seat that edits everything has not respected a draft that
passed its rules. There is no target share. Accept only what you would put your own name to in a child's record;
edit when the idea is right and the sentence is not; skip when the idea itself should not be recorded, and say
why. The draft was written by a model; that earns it no gentleness and no suspicion. Reasons must be about that
line, in plain words a founder can act on, not "fine" or "unclear".

## What you write

One file, JSON, at the path your instructions give. Shape:

```
{
 "seat": "<educator|parent|development|rights>",
 "verdicts": [
   {"id": "<behaviour id>", "verdict": "accept" | "edit" | "skip",
    "reason": "<required for edit and skip, at most 30 words; optional for accept>",
    "edit": {"statement": "...", "adult_sees": "...", "counter_example": "...",
             "capture_mode": "...", "setting": "...", "words": ["..."]}   # edit only; only the fields you change
   }, ...   # every one of the 192 ids exactly once
 ],
 "cells": [  # only cells where you have something to say
   {"capability_id": "...", "stage_id": "...",
    "missing": [ {"statement": "...", "adult_sees": "...", "counter_example": "...", "capture_mode": "...",
                  "setting": "...", "words": ["..."], "why": "<what the cell lacks, one line>"} ],   # at most two
    "duplicates": [["<id>", "<id>"]],   # two behaviours anywhere in the draft that record the same evidence
    "notes": "<one or two sentences>"}
 ],
 "could_not": [ {"capability_id": "...", "verdict": "honest" | "wrong" | "missing", "reason": "..."} ],
 "objections": ["<your three strongest objections to the draft as a whole, one sentence each>"],
 "note_to_founders": "<one paragraph: what you would say to them across the table>"
}
```

Your edited sentences obey every rule above (they will be run through the same code validator). Write the file
with Python in pieces rather than one giant write, then run the checker your instructions name; fix what it
reports until it prints OK. Do not write anything else to the repository.
