# The school operating system — the council's synthesis

26 September 2026 · a proposal for Nimish, Aseem and Achal · **W3, step 6 — this document moves no gate**

**What this is.** Nimish asked for a council on the whole school operating system, of which the assessment
engine is one part. The questions were:

- where AI in schools is heading;
- who has already built the pieces well, and where they fall short;
- how the system should work for each stage and subject;
- how humans stay in charge;
- what "self-learning" can honestly mean.

Nine research seats each took one question. Their sourced notes are in
`research/research_notes/School operating system council/`, and one consolidated report is in
`research/reports/School operating system council.md`. This document is the chair's synthesis. It reads the
research against the three team documents in `docs/sources/`: the Cornerstone Blueprint v2, the Student OS
specification and the SchoolOS PRD. It also reads it against what this repository has already built and
measured.

| Seat | Question |
|---|---|
| 1 | Where AI in schools is heading, and what it means for teachers (the technology committee, with seat 6) |
| 2 | Curriculum systems worldwide |
| 3 | Assessment and measurement products |
| 4 | Observation and documentation |
| 5 | Operations, workload and platforms |
| 6 | Learner modelling and learning loops |
| 7 | Governance, transparency and human oversight |
| 8 | India: policy, infrastructure and products |
| 9 | Subjects and stages, including physical education |

**How to read it.** Section 0 is the whole answer on one page. Sections 1–3 are what the world knows and how
the three documents are reconciled. Sections 4–9 are the design. Sections 10–12 are the risks, what changes
here, and what only the founders can decide.

---

## 0. The answer on one page

Cornerstone should not build "an AI school platform". It should grow the assessment engine's spine into the
school's memory. That spine is one Postgres of dated, confirmed evidence per child. Around it goes a small,
fixed set of assistants. Each assistant does one clerical job, shows its work on a screen, and stops at a gate
sized to the harm its mistakes can do. Children keep working on paper and with people. The AI sits on the
adults' side of the desk. The system learns by writing corrections into rows that are checked before they are
trusted, never by quietly retraining itself.

**The ten decisions the council recommends**

1. **One evidence spine for every subject.** An event is always a child, a competency, a date and a capture
   mode, recording who proposed it and who confirmed it. The capture mode is one of sheet, observation, audio,
   photo, rubric, comparative judgement, the child's voice or the parent's voice. New subjects add capture
   modes, not new systems.
2. **At most ten assistants, and no autonomous agent at run time.** Every model call is one fixed-shape call
   inside a flow that code controls, as ADR 0006 already decided.
3. **Gate by decision class, not by blanket and not by the model's confidence.** What can be checked by code
   and undone settles alone, with blind spot-checks. A judgement, or anything that writes to a child's
   record, is decided by a person. Anything a parent sees is decided by two people. Some things are never
   automated at all (section 6).
4. **Confidence routes nothing until it is measured on our own children.** On the answers people had to type,
   the page reader's "90+" confidence was right 33 times in 42 (ADR 0032). A vendor's confidence is a label,
   not a probability.
5. **Counted, readable mastery rules stay the truth.** Learned models sit beside them as measured, advisory
   layers: ratings for item difficulty and child level now, knowledge tracing in shadow. Deep models are never
   used at this scale.
6. **Paper and people for children; no tests before Grade 3; no screen facing a child under 8.** India's own
   Foundational framework calls tests for ages 3–8 "completely inappropriate".
7. **Nothing scores a child's emotions, body or "risk".** The EU has banned emotion inference in education
   since February 2025. India's data law forbids behavioural monitoring of children, except where a school
   needs it for education or safety.
8. **Reports are shaped like the Holistic Progress Card (HPC).** They show competency levels and a narrative,
   compare the child with their own earlier card, and never rank. Marks never go to Foundational-stage
   parents.
9. **Build the spine and the gates; buy the models, speech, timetabling and commodity operations; integrate by
   export.** No product surveyed holds a per-child skill model. Every product surveyed does fees and
   attendance.
10. **Measure teacher time before and after every assistant.** An assistant that retires no task is not
    switched on.

**Where the council pushes back on the brief**

- *"Every data point helps."* Only confirmed, labelled data helps. Unconfirmed data is noise. Some data must
  never be collected: emotion, body measures in the learning record, continuous behaviour tracking.
- *"Minimise physical evaluation."* Keep the paper. Remove the clerical marking and form-filling around it.
  Every documented backlash was against screen-first schooling of young children.
- *"Save teachers significant time."* That happens only by retiring whole tasks. The one high-quality trial
  found about 25 minutes a week saved on one assisted task. The large figures quoted in the documents are
  projections, not measurements.
- *"Self-learning."* It will be narrower, more auditable and slower than the documents imply. With a few
  hundred children most school-wide patterns stay uncertain (section 8).
- *The PRD and the Student OS specification.* Both are generic architectures. Where they contradict decisions
  this repository measured, the measurements win (section 3).

---

## 1. The 10,000-foot view — where AI in schools is going

The technology committee is seats 1 and 6. It reports five facts, each dated and sourced in the notes.

1. **Capability is getting cheap fast.** The price of a fixed level of model capability is falling roughly
   13-fold a year, per Epoch (September 2026). Treat that as approximate. So do not train or host models.
   The scarce asset is the school's own corrected evidence, which no vendor can sell.
2. **Learning gains come from design, not from the model.**
   - A tutor built to give one step at a time, from a supplied answer key, more than doubled learning
     gains. That study was of 194 Harvard physics undergraduates, not schoolchildren.
   - The same class of model used without guard rails cut unaided exam scores by 17% in a trial of about
     1,000 high-school students.
   - AI that coached the *adult* tutor raised the mastery of about 1,000 elementary maths pupils by 4
     points, and by 9 points under weaker tutors. This is the strongest result for young children, and in
     it the AI faced the adult, not the child.
   - As of September 2026, no frontier lab's school product has an independent study of learning outcomes
     for school-age children.
3. **The weakest capabilities are the ones a paper-first school needs most.**
   - *Handwriting.* No benchmark exists for the handwriting of children from Nursery to Grade 4. The one
     children's study found zero-shot reading "inadequate".
   - *Speech.* No benchmark includes children's speech. On adult phone speech, the best systems score about
     5% word error in Hindi and 9% in Marathi, roughly doubling when the audio is poor.
4. **Regulation is converging on the same four rules.** No emotion inference; no behavioural monitoring of
   children outside education or safety; complete logs; human oversight designed against automation bias, with
   explanations and a way to correct the record. India's children's-data rules apply from 13 May 2027,
   18 months after the Rules were notified. The seat read them from a mirror of the Rules, so verify the
   date against the Gazette.
5. **Measured time savings are modest.** The one high-security trial found 25.3 minutes a week saved on
   lesson planning, with no loss of quality. It also found that teachers almost never refined a draft by
   prompting again. They took the first output and edited it by hand. The often-quoted "13 hours a week" is a
   2020 consultancy projection, not an observation.

**What it means for teachers.** By about 2028 the document work goes:

- marking closed answers;
- making practice sheets;
- drafting notes and reports;
- transcribing.

What stays is reading the individual child, deciding the next step, motivation, relationships and
safeguarding. The job moves from clerk to diagnostician. The documented risk is "deskilling through disuse":
if the system pre-decides, teachers stop exercising judgement. That is one more reason every gate must make a
person decide rather than tick.

**The one model to reject outright: "guides instead of teachers".** Alpha School's public state data show
28% and 10% proficiency in Arizona against 65% and 60% predicted. Five of six states rejected its charter
(ProPublica, 2 September 2026). Software plus guides has no independent support.

---

## 2. What the world has already built — borrow and avoid

Nobody has built what Cornerstone is building. The pieces exist in different places, each with a known limit.

| Area | Who does it well | Borrow | Avoid or limit |
|---|---|---|---|
| Curriculum spine | India's NCF (Curricular Goal → Competency → Learning Outcome) | The vocabulary unchanged; schools own the Learning Outcomes | Competencies alone are too coarse to place a child (13 for five years of maths) |
| Diagnostic grain | Cambridge Primary (about 55 Stage 1 maths objectives), White Rose small steps, ACARA indicators | Hundreds of small steps per subject per stage | One global scale across subjects |
| Levels | ACARA progressions; NZ PaCT | Levels per strand, not tied to grade; a child may straddle levels; report ranges, not points | Levels used as a tick list |
| Prerequisite edges | Clements & Sarama learning trajectories | Ordering within a strand is trial-backed | Treating links between strands as fact; they are expert guesses everywhere |
| Misconceptions | Eedi (8,000+ misconceptions, CC BY 4.0) | Name every wrong answer; re-check about 3 weeks later; mine the open graph | Multiple choice for ages 5–8; detectors raise about 8 false alarms per real catch |
| AI-generated lessons | Oak National Academy's lesson assistant (Aila) | Fixed schema, retrieval from its own corpus first, auto-evaluation as triage, teacher approval | Trusting the evaluator; its agreement with teachers rose only from 0.17 to 0.32 |
| Grouping by level | Pratham's Teaching at the Right Level | A coarse ladder with time-bound regrouping | Expecting it to work without teacher time and mentoring; zero effect where teachers did not adopt it |
| Adaptive tests | NWEA MAP, Renaissance Star, i-Ready | Nothing below age 8 | 25–60 minute screen tests; their weakest validity evidence is for kindergarten |
| Described bands | ACER PAT, e-asTTle | Bands described in words, one scale per subject | Cross-subject composites |
| Paper capture | Gradescope, Remark | Nothing handwritten is final without a check; blank, multiple and crossed-out as first-class states | Any vendor handwriting-accuracy claim; none is published for children |
| Observation record | Tapestry, Storypark, brightwheel | The shared record: media, note, child tags, competency tags, visibility flag | Evidence collected to *prove* a judgement |
| AI disclosure | Storypark's AI fact sheet | Name vendors, regions, retention and fields sent | Storypark sends names; send images only |
| Voice capture | TeachScribe (UK); Sarvam keyterm prompting | Push-to-talk; the roster as key terms; audio replayable in the queue | Any unmeasured accuracy; no product publishes real classroom accuracy |
| Behaviour | — | — | ClassDojo's points, rankings and behaviour feeds |
| School systems | PowerSchool, Veracross, Toddle, Teachmint, Entab, Fedena, Kriyo | Fees, attendance, transport, notices, bought and fed by export | Looking in them for a skill model; none holds one |
| Parent messages | Kraft & Rogers; Bergman & Chan trials | Few, specific, improvement-framed, approved one-sentence notes | "Engagement" as a success measure; feeds and streaks |
| Workload reform | England's DfE toolkit; the 2021 early-years reform | Retire tasks; no evidence-to-prove; fewer data collections | Adding tools on top of unchanged requirements |
| Writing assessment | No More Marking's comparative judgement | Teachers compare two pieces instead of marking; AI takes pairs only after it matches teacher agreement | AI scoring writing unchecked |
| Physical education | TGMD-3; CAPL-2; the PLAY tools | "Shown / not yet" movement skills; self-referenced goals | Sending BMI home; it did not reduce obesity and raised body dissatisfaction (about 30,000 pupils) |

**The failures all share one root: the product came first; evidence, consent and governance came later.**

| Failure | What went wrong |
|---|---|
| inBloom | Closed over consent and opacity, even after a clean security audit |
| AltSchool | Economics that never worked |
| Summit | Screen time and data collection |
| Bridge | Scripted, surveilled teachers |
| LAUSD's iPad plan | An unfinished curriculum |
| LAUSD's chatbot | Pupils' personal data in every prompt |
| Byju's | Selling to parental anxiety |

Cornerstone's rules on names, prompts and evidence answer every one of these, as long as they are enforced by
checks rather than by intent.

---

## 3. The three documents and this repository, reconciled

**Standing.** Blueprint v2 is the house document, and it mostly agrees with what was built. The council
proposes that it **stays the reference, with the five amendments below.** The Student OS specification and
the SchoolOS PRD become background.

Two quality notes on those two background documents:

- **The Student OS PDF cannot be source-checked.** Its references are unresolved placeholders
  ("IciteIturn0search6I").
- **The PRD's model table is about two years old.** It names Claude 3.5, GPT-4o and Gemini 2.0 Flash. So its
  cost claims have no basis: "$0.30–0.50 per student per month" and "grading overhead cut by more than 90%".

| # | Question | Blueprint v2 | Student OS | SchoolOS PRD | This repository | Council ruling |
|---|---|---|---|---|---|---|
| 1 | Workflow runtime | LangGraph-TS, chosen by a spike against n8n | LangGraph or the OpenAI Agents SDK | Temporal plus LangGraph | Engine endpoints plus n8n triggers; a wait is a row (ADRs 0003, 0006) | **Amend the Blueprint: no second runtime.** A human wait is a row in a queue table, visible on a screen and surviving any restart. Revisit only when a step needs a model to choose its own path. |
| 2 | Graph store | Postgres closure table | Postgres plus Neo4j | Neo4j or Memgraph | Postgres closure table | **Postgres.** 244 skills and 849 milestones is small, and joins do not cross databases. |
| 3 | Human gate | Gate everything | Approve what is consequential; an autonomy ladder | Only below 85% confidence or ±2.5σ from the child's average | Right answers settle alone; wrong and blank wait (ADR 0029); per-child floors (ADR 0032) | **By decision class (section 6).** Reject the 85% and ±2.5σ rules. |
| 4 | Mastery model | pyBKT as an offline experiment | Its own state engine | pyBKT as the engine | Counted rules (the level-rule and threshold rows) | **Counted rules stay the truth.** Add ratings with uncertainty nightly; knowledge tracing in shadow only; never deep models. |
| 5 | Decision service | A `decide()` interface; Jev first provider | Jev as the "nervous system" | — | Researched 21 September: not now | **Amend the Blueprint: build the decision registry, drop Jev.** The registry already exists in all but name: prompt rows, the gold set and overturn rates. Jev stays out until it reads images or a real-time need appears, and only after a data-protection review. |
| 6 | Agents | Two: curriculum co-editor and observation extractor | Only inside bounded workflows | Loops for question generation | None (ADR 0006) | **Amend the Blueprint: none at run time.** Observation extraction is one structured call. Curriculum co-editing is a tool the curriculum team drives, not an agent acting on records. |
| 7 | Model routing and cost | Batch calls, caching, a cost line | — | A four-tier routing proxy with a semantic cache | One adapter per service, pinned model ids, a fallback list, cost per run | **Keep the repository's.** Pinned ids matter: a silent model change voids every accuracy measurement. Publish rupees per child per term. |
| 8 | Behaviour over time | Recency weighting; "contested" when adults disagree | Evidence-weighted over time | Exponential decay with a 90-day half-life | — | **There is no behaviour score to decay.** Notes are dated. A pattern needs two adults or two contexts, is written by a teacher, and lapses unless re-confirmed. The 90-day figure has no evidence behind it. |
| 9 | Paper | QR | — | ArUco corners, DataMatrix, Typst | QR at the highest error correction, aligned to the printed PDF | **Keep the repository's.** Phone scan apps crop corner marks, so each photo is aligned to the printed PDF instead. The QR reader decoded 13 of 16 pages of a real photographed file. |
| 10 | Handwriting reader | Bubble reader plus a vision model | "OCR or multimodal" | OpenCV, Surya and a vision model | An OCR service behind the engine's own geometry; a model may propose, never settle (ADRs 0019, 0032) | **Keep the repository's.** A reader that knows arithmetic writes the right answer over the child's wrong one, and no prompt fixes that. |
| 11 | Speech | Sarvam | "An STT provider" | Self-hosted Faster-Whisper on a GPU | — | **Sarvam or Gemini behind one adapter**, with IndicConformer as a self-hosted fallback. No GPU to run. Adults' speech only, until a child benchmark exists. |
| 12 | Build order | Evidence pilot first, assessment in phase 6, curriculum last | A 90-day MVP | An 8-week MVP | BUILD-ORDER steps 6 to 11 | **Amend the Blueprint to the order actually built.** BUILD-ORDER is unchanged; section 11 gives the order after W4. |

The fifth amendment is on stage and paper: see decision 6 in section 0 and section 5.

**Why the documents' timelines are ignored.** They offer eight weeks, 90 days and 28–37 weeks. Blueprint v2
itself calls effort estimates "the least reliable numbers" it contains. The pace is set by human gates, meaning
ratifications, validations and reviews, not by code. Plan by gates.

---

## 4. The system — the spine, the assistants, and what each person gets

### The spine: extended, not replaced

These are the four parts the repository already has, each extended.

**Truth tables.** These keep one rule: append or approve, never edit. They hold:

- the curriculum registry and ladder, with provenance on every prerequisite link (expert, trialled or
  validated);
- the question bank and worksheets;
- captures, results and evidence events;
- the prompts;
- the misconception vocabulary;
- the decision registry.

Observation, artefact, consent and concern tables join them.

**Derived tables.** These are rebuilt nightly and can be truncated at any time. They hold each child's state,
item ratings, the class card and the reader's per-child notebook.

**Adapters.** One file each for handwriting reading, the text model, speech, messaging and exports.

**Flows.** Triggers, waits and notifications only.

Every new subject enters as new *capture modes* on the same evidence event, never as a new store.

### The assistants: at most ten, each one job

| Assistant | Does | Who does the work | Gate | Retires | Status |
|---|---|---|---|---|---|
| **Librarian** | Keeps the question bank and the 1,123 worksheets | Code; the model writes language once | Curriculum team ratifies each skill set | Hunting for and photocopying worksheets | Live (W1) |
| **Dispatcher** | Chooses each child's next paper from their graph and prints the pack with QR codes | Code | Educator approves the pack | Making differentiated papers by hand | Live (W2) |
| **Reader** | Reads photographed papers, marks by lookup, names the mistake | OCR plus code; a model may propose | Right answers settle alone; wrong and blank go to a person | Marking answers that can be computed | Live (W3) |
| **Grapher** | Rebuilds each child's skill state nightly from confirmed evidence | Code | None: derived and disposable | Tallying marks into registers | Live (N10) |
| **Scribe** | Turns an educator's voice note into candidate observations per child | Speech recognition, one structured call, code for names | Educator confirms every item; safeguarding bypasses the queue | Writing anecdotal records | Next |
| **Reporter** | Class card, home sheet, parent note, monthly report, termly HPC | Code assembles; a model drafts sentences from cited evidence; code checks every citation | Educator line by line; coordinator releases | Compiling report cards | W4 |
| **Planner** | Level groups, tomorrow's plan, the re-check schedule | Code | Educator | Planning differentiation by hand | Later |
| **Timetabler** | The FET timetable and absence cover | FET plus n8n | Coordinator | Arranging cover | Later |
| **Curriculum co-writer** | Drafts pedagogy per outcome and level, Oak's way | Model plus validators | Curriculum team, per topic | Lesson planning from nothing | Last |
| **Auditor** | Checks the others: calibration, accept rates, blind seeds, cost, consent, drift | Code | Coordinator, weekly | Nothing; it makes the others trustworthy | Partly live |

The Auditor is partly live today as `engine audit`, `bin/check` and `bin/engine live check`.

### What each person gets

- **Class educator.** Three screens:
  - *Today*: approvals due, the confirm queue, children needing attention, with a reason for each.
  - *The class*: level groups and who has not been seen in four weeks.
  - *The child page*: evidence with counts, observers and last-seen dates; strengths; gaps; what was tried.

  The queue is sorted by kind of judgement, with a daily minutes budget.
- **Assistant educator.**
  - Capture: photographs, sheets and the child's QR stickers.
  - Printing and packing.
  - The "what is written" half of the queue (section 9).
- **Coordinator.** Class exceptions rather than raw rows. Second approval on anything a parent sees. The
  safeguarding path. The observer-bias view.
- **Curriculum team.** Ratification of skill sets, levels, links and mistakes. The misconception analyst's
  list of unexplained wrong answers. Generated pedagogy per topic.
- **Parent.** Few, specific, approved messages. A termly HPC-shaped report in Marathi or English. Their own
  child only, confirmed evidence only, never a comparison. A way to correct the record.
- **Head.** The system map with live numbers, the decision registry, costs, the consent register and the
  time-use results.

---

## 5. How it works for each stage and subject

One rule runs through the table: **evidence moves from observation to paper to rubric as children grow, and
the human gate never disappears.**

| Subject | Foundational: Nursery–G2, ages 3–8 | Preparatory: G3–5 | Middle: G6–8 | Secondary: G9–10 |
|---|---|---|---|---|
| **Maths** | Observation of play and materials. Photographed practice sheets kept as artefacts. No marks to child or parent; levels as icons with a narrative. | Today's weekly loop: differentiated QR worksheets, read, confirmed, graphed. Per-skill bands; a re-check of failed skills after about 3 weeks. | The same loop across more strands. Written working marked by rubric. Difficulty measured from children's answers. | The same, plus practice papers matching CBSE's roughly 50% competency-based share. Internal marks computed from evidence. |
| **Language and literacy** (Marathi, English, third language) | One-to-one oral checks on the ASER levels (letter, word, text). A pseudo-word decoding check near the end of G1. Early writing photographed and judged for developmental stage. Audio kept for moderation. | Reading fluency and comprehension three times a year. Speech recognition pre-scores only after a local accuracy test per language. Writing by comparative judgement across sections. | Writing by rubric and comparative judgement. An AI judge only once it matches teacher-to-teacher agreement. | Board-aligned rubrics; internal marks computed. |
| **EVS, science, social science** | EVS through talk, sorting and drawing, observed | Short answers and diagrams on QR sheets, marked against a rubric of acceptable ideas. Inquiry by observation checklist. Projects by a rubric shared in advance. | Science and social science from G6. Practicals by observation checklist, projects by rubric. | The four parts of CBSE's internal assessment, computed from evidence |
| **Arts and music** | Dated photos and recordings plus the child's dictated reflection. No score. | Portfolio. No score. | Shared-criteria rubrics for performance from G6. Never an AI score. | CBSE school-based art education |
| **Physical education** | "Shown / not yet" for run, hop, jump, throw, catch and balance. Short clips for a second teacher to moderate. **No fitness scores, no BMI.** | From about 8, a profile of competence, confidence, knowledge and activity. Self-referenced goals; never ranks. | Sport skills added. Fitness testing only as a separate health track, with consent and seen only by parents and health staff. | The same |
| **Socio-emotional, learning habits** | The educator's descriptive notes, visible to staff by default. Class-level wellbeing and involvement scans (Leuven), used to improve the room. The child's pictorial self-assessment. **No score, no emotion AI.** | The same, plus the HPC's self and peer sections | Validated questionnaires from about age 8, aggregated for programme review only | The same |
| **Report** | Termly HPC: levels as icons plus a narrative, against the child's own earlier card | HPC plus per-skill bands; a monthly parent note | HPC plus subject bands | CBSE internal assessment plus HPC; two Class X attempts |

The tests Cornerstone runs are the one-to-one oral checks and the weekly worksheets. Each check is logged as
one piece of evidence and never as a verdict from a single sitting. DIBELS's own manual puts the reliability
of a single kindergarten check as low as 0.49.

**The week, by stage**

- **Foundational.** Observation is daily. CBSE's HPC guide suggests focusing on one or two competencies a
  week.
  Artefacts are photographed with the child's QR sticker. One voice note after class goes to the Scribe, with
  confirmation in under two minutes. The HPC is termly.
- **Preparatory.** The agreed week: Monday to Wednesday teach, Thursday differentiated practice, Friday the
  differentiated paper. Then read, confirm and graph. Friday brings the class card and the home sheet; the
  parent report is monthly.
- **Middle and Secondary.** The same loop per subject. Rubric marking replaces lookup for written answers,
  so more items reach a person. The internal marks the board requires are computed from confirmed evidence,
  so every mark is defensible.

---

## 6. Human in the loop — the gate by decision class

The school has already made this decision once, for one kind of answer. ADR 0029 says a right answer settles
on the reader alone, while a wrong or blank answer waits for a person. The reason: a misread almost never
lands exactly on the key, so a right reading has in effect been checked by code, while a misread always
lands on "wrong" or "blank". The council recommends making that reasoning the rule for every decision in the
system.

| Class | What belongs in it | Gate |
|---|---|---|
| **A: checkable by code, reversible** | A reading that equals the computed key; a QR lookup; a name matching the alias table exactly | Settles alone. A random sample is re-checked blind every day. Allowed only after its accuracy is measured on our own children. |
| **B: judgement, or writes to the record** | Which mistake a wrong answer shows; a transcribed observation; anything that changes a child's state beyond a code-checked right answer; a report line | A person decides every item by typing, choosing or correcting. The engine offers its guess. For a fixed sample, the guess stays hidden until the person has answered. |
| **C: seen by a parent or hard to undo** | A report sent home; a change to a child's group or level lasting more than a week; a socio-emotional note that persists | As B, plus a second person (the coordinator) |
| **D: never automated, never inferred** | Emotions, temperament, "risk" scores, BMI in the learning record, rankings, behaviour points | Not built |
| **S: safeguarding** | A concern | Goes at once to the coordinator and the head, ahead of every queue |

**Why neither document's rule survives.**

- *Gating everything* spends reviewers' minutes on things code has already checked. Clinical research shows
  what happens next: people override about 90% of alerts, and review becomes a rubber stamp.
- *Gating only low confidence* trusts numbers that are not probabilities. Language models' confidence is
  poorly calibrated. In clinical studies, wrong advice from a machine raised the risk of a wrong human
  decision by 26%.
- The breast-screening trials show the right way. Machine triage cut radiologists' reading by about 44%
  without missing more cancers, but only after the thresholds were validated in advance.

**The queue, designed against automation bias.** These rules come from seat 7's evidence.

- Lowest confidence first.
- Blind seeds: confident items mixed in unannounced. The step 4 queue already mixes in one confident answer
  per paper, and that is exactly this.
- Decide-then-compare on a fixed sample.
- Every disagreement between model and code, or between two reads, routed to a person.
- Show information, not a recommendation: the crop and the recomputed truth, never a green tick.
- Record who confirmed, when, the time spent and what changed. An accept rate near 100% with very short time
  spent tightens the queue automatically.
- Before any gate is trusted, seed known-wrong readings into it and count how many pass.

**The minutes budget.** Blueprint v2's pilot rule is adopted. If the queue costs more than 5 minutes a day for
a week, or more than a third of items are corrected, the upstream step is fixed. The bar is never lowered.

**Autonomy is earned per decision class, not by the calendar.** The council adopts the Student OS
specification's autonomy ladder: record, suggest, guarded automation, adaptive workflow, closed-loop,
institutional.

- For the first two years: Class A may reach guarded automation; Classes B and C stay at "suggest"; Class D
  stays at "record", written by humans.
- Nothing reaches the adaptive levels until the logs, golden sets and governance to judge it exist.
- A step up needs three things: shadow data, a result that beats the golden set on calibration for that grade
  and channel, and the head's sign-off.

---

## 7. The glass box — what every screen shows

"Not a black box" becomes eight concrete things. The first already exists: the "How it works" page
(`/workflows`) draws `workflows.json` with live numbers.

1. **The system map.** Every assistant's steps, today's counts, queue sizes, last run, failures and cost,
   drawn from the map the code is held to. It is extended to every organ as each one arrives.
2. **Provenance on every artefact.** For example: "Drafted by the Reporter, version 3, from 14 confirmed
   pieces of evidence; confirmed by [name] on [date]." There is no artefact without its trail.
3. **Evidence behind every claim about a child.** The number of events, the number of observers and contexts,
   the last-seen date, and the crops and notes themselves. Below the evidence floor the screen says "not
   enough evidence yet". A disagreement between adults shows as "contested", never as an average.
4. **A reason for every recommendation**, in one sentence of rule text, with the alternative that was not
   chosen.
5. **The decision registry.** Each decision class with:
   - its status: shadow, advisory or autonomous;
   - accuracy on the golden set by grade and channel;
   - a calibration chart;
   - overturn and accept rates;
   - the last version change and who approved it.
6. **Correction.** Any educator or parent can contest a line. The correction is a clocked workflow that writes
   a superseding row, and the original stays.
7. **The AI fact sheet.** Which vendors, which regions, which fields are sent (images and ids, never names),
   and how long anything is kept.
8. **Health and cost.** Per-flow cost, failures and a check that raises an alarm when a job silently stops
   running. Rupees per child per term should visibly fall.

This is also the EU AI Act's high-risk standard adopted voluntarily: logs, documented accuracy, oversight
designed against automation bias, and an explanation of the decision. Marking that steers a child's next work
is exactly the kind of use the Act classes as high-risk.

---

## 8. Self-learning, honestly

**The definition the council recommends.** Four things, all auditable:

1. Every confirmed answer, photo, observation and correction updates each child's state and each question's
   rating that night, by code.
2. Every correction becomes a labelled example that scores the current prompt or rule against the one before
   it.
3. A new version acts on its own only after it beats that golden set, in shadow first, for each grade and
   channel.
4. What cannot be learned locally is borrowed from research and larger populations, then re-checked on our
   own children. That covers item difficulty at the start, spacing and interleaving, and which interventions
   work.

It does **not** mean:

- a model rewriting itself;
- prerequisite links learned from data as fact;
- settings fitted per child;
- claims about which intervention works from the school's own data.

Those four are the black box the brief asks to avoid, and at this scale the statistics cannot support them.

| Loop | Learns from | What changes | Checked by | Human gate | Today |
|---|---|---|---|---|---|
| Reading | Every confirmed or corrected answer | The child's own confidence floor, the kinds routed to a person, digit confusions, handwriting samples | The reader's gold evaluation | People settle every doubtful answer | Live (ADR 0032) |
| Question difficulty | Every confirmed answer | A rating per question and level; misfit flags | Misfit checks once a question has 30+ answers | Curriculum team reviews flags | After W4 |
| Mistake vocabulary | Wrong answers no named mistake explains | New named mistakes | Code reproduces the exact wrong answer | Aseem and the curriculum team name them | Instrument live |
| Names | Every confirmed observation | The alias table | Name-match precision on gold | Educator confirms | With the Scribe |
| Extraction | Educators' edits to candidate observations | Prompt versions | Precision and recall on gold, per grade | A version replaces the last only if it wins | With the Scribe |
| Calibration | Overturn and accept rates per class | Routing thresholds; autonomy level | Calibration by confidence band; blind seeds | Head approves any step up | Partly live |
| Prerequisite links | Children failing skills together | Flags only | Curriculum team review | Never automatic | Later |
| Pedagogy | Educators' feedback on activities; outcomes | Revision proposals | Termly review | Curriculum team | Last |
| Workload | Queue minutes; the time-use survey | Upstream fixes | The survey | Head | Start now |
| Cost | Cost per run | Model and prompt choices | Rupees per child per term | Head | Live |

**The limits, in numbers, at 60 children** (seat 6, computed):

| What you measure | What you can conclude |
|---|---|
| A mistake that truly affects 10% of children | It can read anywhere from 5% to 20% |
| A child's success rate on a skill after 20 attempts | Still uncertain by about ten points either way |
| Two groups of 60 compared | Only large effects are detectable (d about 0.5); realistic effects are 0.1 to 0.4 |

So patterns per child over time: **yes**. Item and mistake statistics across the school: **yes, shown with
their uncertainty**. "Which intervention works": **borrowed from research and watched child by child**, never
claimed from our own data.

---

## 9. The teacher's team — the people

The brief's image is a teacher with their own team. The council's version is this.

| Role | Owns |
|---|---|
| **Class educator** | Every judgement about a child; one-to-one diagnostic conversations; Class B decisions; the narrative; parent conferences |
| **Assistant educator** (per class or pair of classes) | Capture and printing; the "what is written" half of the queue; structured practice under the educator's plan |
| **Academic coordinator** | Second approval on Class C; releasing reports; safeguarding with the head; the observer-bias review |
| **Operations and data coordinator** (one per school) | The system map's health, queue health, golden sets and blind seeds; the consent register; vendor exports; the time-use survey; the cost line |
| **Curriculum team** | Skill sets, levels, links and mistakes; generated pedagogy |
| **Head** | Policy; every step up the autonomy ladder; final authority |

**The queue split that returns the most time.**

- *What is written.* "Is this a 7?" A careful adult can settle it. The engine then computes the mark and names
  the mistake, as ADR 0029 already does for any person's reading.
- *What it means.* Which mistake, what next. This needs the educator.

Giving the first half to assistant educators keeps educators' minutes for the second. The evidence on
teaching assistants supports exactly this: they supplement and never replace, and supportive tasks free
teachers.

**Hiring.**

- *Educators.* Hire for diagnostic judgement and evidence literacy, not "AI skills". Look for strong
  early-maths and early-literacy teaching knowledge, and a willingness to overrule the machine. Screen with
  real anonymised sheets: "What does this child misunderstand, and what would you do on Monday?"
- *Assistant educators.* Hire for reliability, care, basic digital fluency, and Marathi and English.

**Training.**

- Deciding before comparing, in the queue.
- Reading a child page.
- Writing specific observations ("counted 7 objects with one-to-one correspondence"), never global labels.

**Returned time is redeployed on purpose,** into one-to-one and small-group diagnostic work. In the EEF trial,
that is where teachers put the time they saved.

---

## 10. Pros, cons and risks

| | Why |
|---|---|
| **Pro: assets that compound** | The misconception-tagged bank, per-child longitudinal evidence and golden sets exist only here. Engines can be rebuilt; these cannot be bought. |
| **Pro: transparent by construction** | Rows, provenance and the map page already exist; the design adds no hidden state. |
| **Pro: ready for the law** | DPDP's rules on children, and the EU's high-risk bar adopted voluntarily |
| **Pro: amplifies teachers** | Every large positive result in the literature had teachers structurally in the loop. |
| **Pro: cheap to run** | Intelligence is spent at design time. The whole bank's model spend must stay under a ₹50 gate, and one matching job cost ₹39 in total. |
| **Con: human gates cost minutes** | Reviewer time is the binding constraint; the design spends it only where harm is possible. |
| **Risk: reading children's handwriting** | 81.9% exact on the gold (ADR 0028); most doubtful answers need a person. Mitigation: the per-child notebook; the queue split. |
| **Risk: children's speech is untested** | Mitigation: speech for adults' notes only; children's oral reading only after a local test per language |
| **Risk: over-documentation** | England's lesson. Mitigation: no evidence-to-prove; no per-child quotas; success means less documentation time |
| **Risk: automation bias** | Mitigation: section 6's queue design, measured |
| **Risk: labelling children** | Mitigation: no standing labels; derived states expire; evidence shown, not verdicts |
| **Risk: data protection deadline** | Consent flows, lawful-basis tags, one-year access logs and correction with notification, by 13 May 2027 |
| **Risk: vendor dependence** | OCR, the text model and speech. Mitigation: one adapter file each; pinned ids; gold evaluations before any switch |
| **Risk: the curriculum review bottleneck** | Blueprint v2: "No architecture fixes an unreviewed curriculum". Mitigation: approval by topic, not by 1,750 objectives |
| **Risk: teacher adoption** | "A teacher who sees nothing come back stops on day four" (Blueprint v2). Mitigation: a weekly five-line "what the system now knows" back to each educator |
| **Risk: a team of one founder plus AI** | Mitigation: one runtime, one database, ten assistants at most, everything checked by commands |

---

## 11. What this changes for the repository, and what it does not

**Unchanged.** `BUILD-ORDER.md`, its sequence and its gates. W3 step 6 continues. No code, prompt,
migration, endpoint or screen for any new organ starts before W4 closes.

**Six things to fold into the steps already planned** (no new workflow):

1. **W4's parent report (step 11) is HPC-shaped.**
   - Competency levels plus a narrative; the child against their own earlier self; the yardstick named.
   - Marathi and English.
   - **No marks for Grades 1–2.**

   The Foundational framework allows worksheets as the child's work, but not tests. So Grade 1–2 papers
   should be framed and reported as practice artefacts, not assessments. This is a question for Aseem and
   Achal before W4 is written.
2. **The queue (step 4, live) gains decide-then-compare** on a small fixed sample, and records time spent. The
   blind spot-check already exists.
3. **"Not enough evidence yet"** must appear on the child page wherever the counted floor is not met. Check
   the six-state rules against this.
4. **Easy, Medium, Hard and Advance are measured complexity, not measured difficulty.** The region rules
   measure operands, regrouping and layout. Only children's answers measure difficulty. After W4, add ratings
   computed from responses beside the four labels. Never replace the labels.
5. **Before any observation work, two things.** A consent and lawful-basis design under DPDP. A two-week
   teacher time-use baseline (a reference-week survey), so "time returned" can be proved by a command like
   every other claim.
6. **ADR 0035 (proposed) records the rejected alternatives** from the three documents. That way a later
   session reading `docs/sources/` does not act on LangGraph, Neo4j, Temporal or Jev by mistake.

**After W4, the order of new organs the council proposes:**

1. **The Scribe and Foundational observation.** Three of the school's grades (Nursery to Grade 2) cannot be
   served by worksheets under the national framework. Its golden set already exists: Maya ma'am's voice
   notes.
2. **The termly HPC,** assembled from both streams.
3. **Literacy as the second subject,** starting with teacher-scored oral checks captured as evidence, with
   speech recognition only after a local test.
4. **Educator Today, parent notes and the Planner's level groups.**
5. **The Timetabler,** with FET and the cover flow.
6. **The curriculum co-writer, last.** It needs classroom evidence behind it, and its reviewers are the
   scarcest people.

---

## 12. Decisions only the founders can take

1. **The board**: CBSE, Maharashtra State Board or another. It decides the report format, the HPC vocabulary
   and everything for Grades 9–10.
2. **The HPC vocabulary.** Beginner/Progressing/Proficient or Stream/Mountain/Sky: the official documents
   disagree, so it stays a row, not code.
3. **The Foundational framing** of Grade 1–2 papers (section 11, item 1).
4. **The observation pilot**: which educators and classes, and whether safeguarding runs through the same
   channel.
5. **Consent policy**: the lawful basis per data element, and whether any child's work may ever help improve
   a vendor's model. The default is no.
6. **Assistant educators**: whether the school hires them, and in what ratio.
7. **Physical education**: whether any fitness testing happens, and if so as a separate consented health
   track.
8. **Kriyo**: confirm the vendor and its domain (one seat found the domain redirecting elsewhere; unverified),
   and make a data export a renewal condition.
9. **The time-use baseline**: when it runs, and the target. England's taskforce chose 5 hours a week within
   three years; that is a reference, not a promise.

---

*Evidence for every claim above is in the nine seats' notes, each with the links actually opened. Where a
seat could not open a primary source, the claim is marked unverified there and kept out of the rulings here.
The research ran nine seats and one report writer. The shared web-search allowance ran out midway, so later
sourcing went to official pages directly, and the gaps are listed in each seat's notes.*
