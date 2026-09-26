# Level 2 draft for the founders' sitting — observable behaviours per capability per stage

26 September 2026 · a draft to edit, not a decision · **no step of the build order moved — nothing built**

**How this was made.** The ratified prompt (`docs/school-os-proposal-capability-behaviours.md`, §3) was run once by hand in the council session, not by the engine, and its output was checked by the proposal's validator as a script: `python3 research/level2_validate.py docs/school-os-level2-behaviours-draft.json`. First pass: 25 of 32 cells passed; the seven that failed were regenerated once with the failures named, and the second pass was 32 of 32.

**Then a council of four seats read every line** (educator, parent, developmental and measurement expert, child-rights and safeguarding), each from its own life, and marked Accept, Edit or Skip with a reason. Their verdicts were reconciled by rules (`research/level2_council.py`): 94 rows stand as written, 90 were edited, 8 retired (struck through below, kept so you can restore them), 20 added. The column **Council** shows each seat's verdict (E educator, P parent, D development, R rights) and what was done; every change and its reason is in `docs/school-os-level2-council-changes.md`. This is the council's pass, not yours: your acceptance rate is still the eval the proposal names.

**What to do.** For each behaviour, mark one of **Accept · Edit · Skip** in the last column. Edit means rewrite it in your own words on the line; Skip retires it. Add a behaviour where a cell is missing something you would look for. Your edits become the golden set. Two founders split the eight capabilities; the third settles any cell you disagree on.

**The three words, in the draft meanings the tags follow** (replace with your own before the engine runs):

- **capable** — knows things deeply and can do something with them; can find out what they do not know.
- **kind** — notices other people and acts for them, including when it costs something.
- **unafraid** — tries, asks, disagrees and shows their work in front of others, and treats a wrong answer as information.

Every behaviour is one occasion a familiar adult could see and record, never a level, a score or a trait. The stage rises: a later behaviour grows out of a named earlier one. "Not evidence when" is the look-alike an educator should not count.


## Knowledge & academic mastery

*Observable at 16:* Strong conceptual and procedural command of core subjects; can perform under examination conditions.


### Foundational · Nursery to Grade 2 · ages 3–8 · Discover

| # | Behaviour | What the educator sees | Where · how | Words | Not evidence when | Grows from | Council | Accept · Edit · Skip |
|---|---|---|---|---|---|---|---|---|
| 1 | Counts a set of objects up to ten, touching each once and saying one number for each. | The educator watches the child's finger and voice keep step through the set. | play · observation note · from age 4 | capable | Recites numbers to ten faster than the finger moves, skipping or double-touching objects. | — | R:A D:A E:A P:A → **accepted** |  |
| 2 | Reads a familiar word aloud from a word card or a label that has no picture beside it. | The educator points to a word on the word wall or a label and hears it read from its letters. | lesson · observation note · from age 6 | capable | Names the label by where it hangs and cannot read the same word on a card held elsewhere. | — | R:A D:A E:E P:A → **edited** |  |
| 3 | Exchanges ten single blocks for one ten-rod when asked how many tens are in a pile. | The educator sees the child make the exchange and name the rod as one ten. | practice · observation note · from age 7 | capable | Moves blocks into a row of ten without naming it as one ten. | — | R:A D:A E:A P:A → **accepted** |  |
| 4 | Retells a story just heard with its beginning, middle and end in the right order. | The educator hears the events come in the order the story had them. | circle · observation note · from age 5 | capable | Names characters from the story without the events in order. | — | R:A D:A E:E P:A → **edited** |  |
| 5 | Sorts a mixed set of objects by a rule the educator names, and says the rule back. | The educator sees the sort match the rule and hears the child state it. | play · observation note · from age 4 | capable | Sorts by a rule of their own and cannot say what it was. | — | R:A D:A E:A P:A → **accepted** |  |
| 6 | Writes or forms their own name and the numerals one to nine, on paper or with tiles, from memory, so another adult reads them back. | The educator sees no model in view and a second adult reads the name and numerals back, in any script the child is learning. | lesson · artefact · from age 5 | capable | Traces the name over a dotted model. | — | R:E D:E E:A P:A → **edited** (chair) |  |
| 7 | Uses a word taught this week in a sentence of their own about something in the room. | The educator hears the week's word in a sentence the child made, about a thing in view. | lesson · observation note · from age 4 | capable | Repeats the sentence the educator used to teach the word. | — |  → **added** (chair) |  |

### Preparatory · Grades 3–5 · Investigate

| # | Behaviour | What the educator sees | Where · how | Words | Not evidence when | Grows from | Council | Accept · Edit · Skip |
|---|---|---|---|---|---|---|---|---|
| 1 | Adds two three-digit numbers with regrouping on paper, showing the exchange in the working. | The educator sees the carried ten written in the working, not only the total. | practice · sheet | capable | Writes the correct total with no working shown. | exchanges-ten-ones | R:A D:A E:A P:A → **accepted** |  |
| 2 | Reads a grade-level passage aloud and answers a question whose answer is stated in the text, reading out the line that says it. | The educator hears the passage read, the answer given, and the line from the text read out as its source. | lesson · audio | capable | Answers from general knowledge and cannot find the line in the text. | reads-a-familiar-word | R:A D:A E:E P:A → **edited** |  |
| 3 | Explains a science or geography fact just taught in their own words, with a because. | The educator hears the fact restated differently from the book, with a reason attached. | lesson · observation note | capable | Repeats the textbook sentence word for word. | sorts-by-a-stated-rule | R:A D:A E:A P:A → **accepted** |  |
| 4 | Measures a length or a volume with the right tool and records it with its unit. | The educator sees the tool chosen fit the quantity and the unit written beside the number. | project · artefact | capable | Writes a number without a unit or with the wrong tool's unit. | exchanges-ten-ones | R:A D:A E:A P:A → **accepted** |  |
| 5 | Completes a short timed practice set within the time allotted to them and re-works one answer in the margin before handing in. | The educator sees the set finished within the child's allotted time and one answer worked a second time in the margin. | practice · sheet | capable | Finishes early and sits with the sheet untouched until time is called. | writes-name-and-numerals | R:E D:E E:E P:A → **edited** (chair) |  |
| 6 | Writes a paragraph of four or more sentences on one topic, with a first sentence that says what it is about. | The educator reads a first sentence that announces the topic and sentences that stay on it. | lesson · artefact | capable | Writes four sentences on four different things. | retells-a-story-in-order | R:A D:A E:A P:A → **accepted** |  |
| 7 | Reads a short passage aloud in a taught language that is not their home language and answers one question in it. | The educator hears the reading and the answer both in that language, in its lesson. | lesson · observation note | capable | Sounds out the passage correctly, then gives the answer in the language they speak at home. | reads-a-familiar-word |  → **added** (chair) |  |
| 8 | Asks a question in a lesson that names the exact part they did not understand. | The educator hears the question point to one step, one word or one line, not to the whole topic. | lesson · observation note | unafraid, capable | Asks the educator to explain the whole topic again from the start. | sorts-by-a-stated-rule |  → **added** (chair) |  |

### Middle · Grades 6–8 · Apply

| # | Behaviour | What the educator sees | Where · how | Words | Not evidence when | Grows from | Council | Accept · Edit · Skip |
|---|---|---|---|---|---|---|---|---|
| 1 | Solves a problem needing three or more steps, laying out each step so another student could follow it. | The educator can follow the working from the first step to the answer without asking. | practice · sheet | capable | Reaches the right answer with steps missing or out of order. | adds-with-regrouping | R:A D:A E:A P:A → **accepted** |  |
| 2 | Summarises a textbook chapter in ten sentences that keep its main claims and drop its examples. | The educator reads claims in the child's words and no copied examples. | lesson · artefact | capable | Copies the chapter's first sentences in order. | reads-and-answers-a-passage | R:A D:A E:A P:A → **accepted** |  |
| 3 | Uses a subject's technical term correctly in an explanation, and gives a plain-words version when asked. | The educator hears the term fit its meaning and a plain version follow on request. | lesson · observation note | capable | Uses the term correctly in a rehearsed sentence and cannot give a plain-words version when asked. | explains-a-fact-with-a-because | R:A D:E E:A P:A → **edited** |  |
| 4 | Records an experiment's method, readings and result in a table, with units, on the day it is done. | The educator sees the table filled during the practical, units included. | project · artefact | capable | Writes the expected result before taking the readings. | uses-a-measuring-tool | R:A D:A E:A P:A → **accepted** |  |
| 5 | Sits a full-period written test under exam rules and attempts every question, showing working where asked. | The educator sees every question attempted and working where the paper asks for it. | practice · test | capable, unafraid | Leaves the last questions blank with time remaining. | completes-a-timed-set | R:A D:A E:A P:A → **accepted** |  |
| 6 | Writes an essay of several paragraphs that explains a process or event using facts from the unit. | The educator reads paragraphs that each carry a different part of the explanation. | lesson · artefact | capable | Writes several paragraphs that restate one point. | writes-a-paragraph-with-a-main-idea | R:A D:A E:A P:A → **accepted** |  |
| 7 | Volunteers to work through their own wrong answer on the board with the class, saying where it went wrong. | The educator hears the offer come from the child, then sees them at the board pointing to the step that went wrong. | lesson · observation note | unafraid, capable | Works through the wrong answer at the board because the educator called them up. | asks-what-exactly-was-not-understood |  → **added** (chair) |  |

### Secondary · Grades 9–10 · Create & Question

| # | Behaviour | What the educator sees | Where · how | Words | Not evidence when | Grows from | Council | Accept · Edit · Skip |
|---|---|---|---|---|---|---|---|---|
| 1 | Solves an unseen problem in the board's format by choosing which method applies, and writes one line on why that method. | The educator reads a method that fits the problem and a written line giving the reason for choosing it. | practice · test | capable | Applies the method just practised whether or not it fits. | solves-a-multi-step-problem | R:A D:E E:E P:A → **edited** (chair) |  |
| 2 | Reads a primary source or a research abstract and states its claim and its evidence separately. | The educator sees the claim and the evidence written as two separate things. | lesson · artefact | capable | Summarises the source's topic without separating claim from evidence. | summarises-a-chapter | R:A D:A E:A P:A → **accepted** |  |
| 3 | Teaches a concept from their own subject to a younger student, using two different explanations. | The educator hears the second explanation differ from the first when the first does not land, and notes it without the younger child's name. | project · observation note | capable, kind | Reads their notes aloud to the younger student. | uses-a-technical-term-correctly | R:E D:E E:E P:A → **edited** |  |
| 4 | Derives a formula or result from first principles on paper, rather than quoting it. | The educator sees the derivation start from definitions, not from the formula. | lesson · artefact | capable | Quotes the formula and substitutes numbers. | records-an-experiment | R:A D:A E:A P:A → **accepted** |  |
| 5 | Completes a full board-pattern examination under exam conditions, managing time across all sections. | The educator sees every section attempted within the time. | practice · test | capable, unafraid | Runs out of time with a whole section unattempted. | sits-a-full-length-test | R:A D:A E:A P:A → **accepted** |  |
| 6 | Writes an extended piece that argues a position using sources cited by name. | The educator sees named sources and a position that rests on them. | project · artefact | capable | Lists sources at the end that the argument itself never uses. | writes-an-explanatory-essay | R:A D:A E:A P:E → **edited** |  |

## Thinking & reasoning

*Observable at 16:* Defines problems, evaluates evidence, reasons quantitatively and changes position when evidence warrants.


### Foundational · Nursery to Grade 2 · ages 3–8 · Discover

| # | Behaviour | What the educator sees | Where · how | Words | Not evidence when | Grows from | Council | Accept · Edit · Skip |
|---|---|---|---|---|---|---|---|---|
| 1 | Asks a why question about something just seen or heard, such as why the ice melted. | The educator hears a why that follows from the moment, not from a book. | circle · observation note · from age 3 | capable, unafraid | Asks 'why' again to each answer without waiting to hear it, as a way of keeping the adult talking. | — | R:A D:E E:A P:A → **edited** |  |
| 2 | Says what will happen before a simple test, such as which object will sink, and then checks. | The educator hears the prediction before the object touches the water. | play · observation note · from age 4 | capable | Says the answer after seeing the result. | — | R:A D:A E:A P:A → **accepted** |  |
| 3 | Gives a reason for a choice when asked, such as why this block goes on the bottom. | The educator hears a reason that refers to the block, not just to wanting it. | play · observation note · from age 4 | capable | Says 'because' and repeats the choice. | — | R:A D:A E:A P:A → **accepted** |  |
| 4 | Points out one way two things are the same and one way they differ. | The educator hears both a likeness and a difference named. | lesson · observation note · from age 4 | capable | Names only what each thing is. | — | R:A D:A E:A P:A → **accepted** |  |
| 5 | Changes a guess after seeing a result that does not match it, and says so. | The educator hears the child say the guess was wrong and give the new one. | play · observation note · from age 5 | unafraid, capable | Repeats the first guess after seeing the result. | — | R:A D:A E:A P:A → **accepted** |  |
| 6 | Says which of two events happened first and which one made the other happen, in a story or a game. | The educator hears the order and the cause both stated. | circle · observation note · from age 5 | capable | Lists both events without saying which caused which. | — | R:A D:A E:E P:A → **edited** |  |

### Preparatory · Grades 3–5 · Investigate

| # | Behaviour | What the educator sees | Where · how | Words | Not evidence when | Grows from | Council | Accept · Edit · Skip |
|---|---|---|---|---|---|---|---|---|
| 1 | Turns a wondering into a question that can be tested in class, such as does the plant grow faster near the window. | The educator hears a question the class could actually set up and answer. | project · observation note | capable, unafraid | Asks a question no one in the room could test. | asks-why-about-something-seen | R:A D:A E:A P:A → **accepted** |  |
| 2 | Writes a prediction before an investigation and the result after, and states whether they matched. | The educator sees the prediction dated before the result. | project · artefact | capable | Writes the prediction after the result is known. | predicts-then-checks | R:A D:A E:A P:A → **accepted** |  |
| 3 | Backs a claim with one piece of evidence from something read, measured or observed. | The educator hears or reads the evidence named beside the claim. | lesson · observation note | capable | Backs a claim with 'everyone knows'. | gives-a-reason-for-a-choice | R:A D:A E:A P:A → **accepted** |  |
| 4 | Spots a pattern in a table or chart, such as one column larger in every row, and says what it might mean. | The educator hears the pattern described and a meaning offered. | lesson · observation note | capable | Reads single values from the chart without a pattern. | notices-a-difference-between-two-things | R:A D:E E:E P:A → **edited** |  |
| 5 | Changes an answer after new evidence and writes the reason for the change beside it. | The educator sees the old answer, the new one and the reason, all visible. | practice · sheet | unafraid, capable | Rubs out the first answer so the change is invisible. | changes-a-guess-when-shown | R:A D:A E:A P:A → **accepted** |  |
| 6 | Sorts statements about a topic into facts and opinions and explains one sorting. | The educator sees the sort and hears one placement justified. | lesson · artefact | capable | Sorts by whether the statement agrees with their own view. | puts-events-in-cause-order | R:A D:A E:A P:A → **accepted** |  |

### Middle · Grades 6–8 · Apply

| # | Behaviour | What the educator sees | Where · how | Words | Not evidence when | Grows from | Council | Accept · Edit · Skip |
|---|---|---|---|---|---|---|---|---|
| 1 | Designs a fair test with one thing changed and the rest kept the same, and names what is kept the same. | The educator sees one variable changed and the controls listed. | project · artefact | capable | Changes two things at once and reports a result. | asks-a-question-that-can-be-tested | R:A D:A E:A P:A → **accepted** |  |
| 2 | Judges whether a source is trustworthy by who wrote it, when and why, before using it. | The educator sees the author, date and purpose noted before the source is cited. | lesson · artefact | capable | Uses the first search result without saying who wrote it. | gives-evidence-for-a-claim | R:A D:A E:A P:A → **accepted** |  |
| 3 | Estimates the size of an answer before calculating and writes whether the calculated result agrees with the estimate. | The educator sees the estimate written above the working and a tick or a note comparing it with the answer. | practice · sheet | capable | Writes an estimate after the calculation that matches the answer exactly. | spots-a-pattern-in-data | R:A D:E E:E P:A → **edited** (chair) |  |
| 4 | Names an assumption in an argument, their own or another's, and says what changes if it is false. | The educator hears the assumption named and its consequence traced. | lesson · observation note | capable, unafraid | Restates the argument's conclusion and calls it the assumption. | separates-fact-from-opinion | R:A D:E E:A P:A → **edited** |  |
| 5 | Concedes a point in a discussion when the other side's evidence is stronger, and says which evidence moved them. | The educator hears the concession and the evidence named. | project · observation note | unafraid, capable, kind | Says 'fine, you win' to end the exchange without naming any evidence. | revises-an-answer-with-a-stated-reason | R:A D:E E:A P:A → **edited** |  |
| 6 | Puts a number on a claim, such as how much faster, and says how it was measured. | The educator sees the number and the measurement it rests on. | project · artefact | capable | Says 'much faster' without a measurement. | records-a-prediction-and-result | R:A D:A E:A P:A → **accepted** |  |

### Secondary · Grades 9–10 · Create & Question

| # | Behaviour | What the educator sees | Where · how | Words | Not evidence when | Grows from | Council | Accept · Edit · Skip |
|---|---|---|---|---|---|---|---|---|
| 1 | Writes a problem statement that says what is known, what is asked and what would count as solved, before starting. | The educator sees the statement written before any working. | project · artefact | capable | Starts computing before saying what the question is. | designs-a-fair-test | R:A D:A E:A P:A → **accepted** |  |
| 2 | Weighs two sources that disagree and explains in writing which to trust more and why. | The educator reads both sources named and a reasoned choice between them. | lesson · artefact | capable | Picks the source that agrees with their first view. | judges-a-source | R:A D:A E:A P:A → **accepted** |  |
| 3 | Checks a result by a second method or by trying an extreme case, and reports the check alongside the answer. | The educator sees the second method or the extreme case written beside the answer. | practice · sheet | capable | Reports the answer with a note that it 'seems right'. | estimates-before-calculating | R:A D:A E:A P:E → **edited** |  |
| 4 | Uses a model or a formula to predict a case not yet seen, then compares with a measurement. | The educator sees the prediction made before the measurement and the comparison after. | project · artefact | capable | Fits a model to data already seen and stops. | quantifies-a-claim | R:A D:A E:A P:A → **accepted** |  |
| 5 | Records a change of position on a question in writing, stating the evidence that changed it. | The educator reads the earlier position, the later one and the evidence between. | lesson · artefact | unafraid, capable | Presents the final position as if it had been held from the start. | concedes-a-point-in-a-debate | R:A D:A E:A P:A → **accepted** |  |
| 6 | Identifies the specific flaw in a flawed argument, such as a sample too small or a cause confused with a correlation. | The educator reads the flaw named precisely in the child's written response, such as the sample size or cause confused with correlation. | lesson · artefact | capable | Calls the argument 'wrong' without naming the flaw. | states-an-assumption | R:A D:E E:E P:A → **edited** (chair) |  |

## Learning & agency

*Observable at 16:* Sets goals, researches independently, seeks feedback, reflects and improves.


### Foundational · Nursery to Grade 2 · ages 3–8 · Discover

| # | Behaviour | What the educator sees | Where · how | Words | Not evidence when | Grows from | Council | Accept · Edit · Skip |
|---|---|---|---|---|---|---|---|---|
| 1 | Chooses an activity with an end point, such as a puzzle or a painting, at free-choice time and stays with it to the end. | The educator sees the activity chosen unprompted and the puzzle completed or the painting declared done by the child. | play · observation note · from age 3 | capable | Finishes an activity the educator assigned rather than one they chose themselves. | — | R:E D:E E:A P:E → **edited** (chair) |  |
| 2 | Tries a task on their own first and then asks for help with the specific part that is hard. | The educator sees an attempt before the request and hears the hard part named. | practice · observation note · from age 4 | unafraid, capable | Asks for help before touching the task. | — | R:A D:A E:A P:A → **accepted** |  |
| 3 | Tells an adult one thing they learned or could do today that they could not do before. | The educator hears a learning named, not an activity listed. | circle · observation note · from age 5 | capable | Names an activity done today without what was learned. | — | R:E D:A E:E P:A → **edited** |  |
| 4 | Fixes a mistake in their own work after one hint, without the adult doing it for them. | The educator gives one hint and sees the child make the correction. | practice · observation note · from age 4 | capable | Waits for the adult to correct it. | — | R:A D:A E:A P:A → **accepted** |  |
| 5 | Puts materials back where they belong so the next child can use them, without being told. | The educator sees the materials returned to their place unprompted. | play · observation note · from age 3 | capable, kind | Puts materials away only when asked by name. | — | R:A D:S E:A P:A → **accepted** (chair) |  |
| 6 | Tries again, in the same session, at something that failed the first time, such as a tower or a jump. | The educator sees the second attempt follow the first failure. | outdoors · observation note · from age 3 | unafraid | Tries again after an adult says 'try once more'. | — | R:A D:E E:A P:A → **edited** |  |
| 7 | Names something they want to learn to do, such as tying laces or writing a letter, and asks to be shown. | The educator hears the wish named and the request to be shown, unprompted. | play · observation note · from age 4 | capable, unafraid | Agrees to learn what the educator proposes. | — |  → **added** (chair) |  |

### Preparatory · Grades 3–5 · Investigate

| # | Behaviour | What the educator sees | Where · how | Words | Not evidence when | Grows from | Council | Accept · Edit · Skip |
|---|---|---|---|---|---|---|---|---|
| 1 | Writes one learning goal for the week in their own words and marks on Friday whether it was met. | The educator reads a goal in the child's words and sees it reviewed on Friday. | lesson · artefact | capable | Copies the class goal from the board. | names-something-they-want-to-learn | R:A D:A E:E P:A → **edited** |  |
| 2 | Looks up an answer in a book, chart or dictionary before asking the educator. | The educator sees the resource opened before the hand goes up. | practice · observation note | capable | Asks the educator the spelling of a word on the word wall. | asks-for-help-after-trying | R:A D:A E:A P:A → **accepted** |  |
| 3 | Names, in a reflection, what was hard about a task and one thing to do differently next time. | The educator reads or hears a specific difficulty and a specific change, and notes that both were named rather than filing the words. | lesson · observation note | capable | Writes 'it was easy' or 'it was hard' without a why. | says-what-they-learned-today | R:E D:A E:E P:A → **edited** (chair) |  |
| 4 | Uses a written comment from the educator to change the next draft, and can point to the change. | The educator sees the commented point changed in the next draft. | lesson · artefact | capable | Rewrites the draft without touching the point commented on. | fixes-own-work-after-a-hint | R:A D:A E:A P:A → **accepted** |  |
| 5 | Keeps their own record of practice sheets done and skills mastered, and updates it unprompted. | The educator sees the record current without having asked. | practice · artefact | capable | Fills the record only when the educator checks it. | puts-materials-back-ready-for-next | R:A D:A E:A P:A → **accepted** |  |
| 6 | Chooses the Hard or Advance version of a task when offered a choice of difficulty, and attempts it. | The educator sees the Hard or Advance sheet taken from the choice offered and worked on. | practice · observation note | unafraid, capable | Chooses the harder version and hands it in blank. | tries-again-after-a-fail | R:A D:A E:E P:A → **edited** |  |

### Middle · Grades 6–8 · Apply

| # | Behaviour | What the educator sees | Where · how | Words | Not evidence when | Grows from | Council | Accept · Edit · Skip |
|---|---|---|---|---|---|---|---|---|
| 1 | Breaks a multi-week project into dated steps at the start and shows, at a check-in, the steps done so far ticked. | The educator sees the plan dated from the start of the project, with the steps completed so far ticked, at a check-in. | project · artefact | capable | Writes the plan on the last day. | sets-a-goal-for-the-week | R:A D:A E:E P:A → **edited** |  |
| 2 | Finds two sources on a topic without help and notes where each was found. | The educator sees two sources located by the child and their origins noted. | project · artefact | capable | Notes two sources that were both handed to them by the educator. | uses-a-resource-before-asking | R:A D:A E:A P:E → **edited** |  |
| 3 | Asks a peer or educator for feedback on one named aspect of their work before it is due. | The educator hears the aspect named in the request. | project · observation note | unafraid, capable | Asks 'is this good?' about the whole piece. | names-what-was-hard-and-why | R:A D:A E:A P:A → **accepted** |  |
| 4 | Marks their own work against the rubric before submitting and notes where it falls short. | The educator sees the self-marking with at least one shortfall named. | lesson · artefact | capable | Awards full marks on every line. | uses-feedback-in-the-next-draft | R:A D:A E:A P:A → **accepted** |  |
| 5 | Reads their own skill map, names a gap, and chooses practice for it. | The educator sees the gap named and the practice chosen to match it. | practice · observation note | capable | Practises only skills already secure. | keeps-own-record-of-practice | R:A D:A E:A P:A → **accepted** |  |
| 6 | Keeps working on a problem after a first attempt fails, trying a different approach within the session. | The educator sees a second, different approach follow the failed one. | practice · observation note | unafraid | Repeats the same failed approach three times. | chooses-a-harder-version-when-offered | R:A D:A E:A P:A → **accepted** |  |

### Secondary · Grades 9–10 · Create & Question

| # | Behaviour | What the educator sees | Where · how | Words | Not evidence when | Grows from | Council | Accept · Edit · Skip |
|---|---|---|---|---|---|---|---|---|
| 1 | Completes an independent study from question to finished product and shows the milestones they set with the date each was met. | The educator sees the finished study and, beside it, the child's own milestones with the dates they were met. | project · artefact | capable | Presents the product with a plan written in the final week. | plans-a-multi-week-project | R:A D:E E:E P:A → **edited** (chair) |  |
| 2 | Reviews their own bibliography and drops or replaces an unreliable source, saying why. | The educator sees a source removed and the reason recorded. | project · artefact | capable | Adds sources to lengthen the list. | finds-and-cites-two-sources-alone | R:A D:A E:A P:A → **accepted** |  |
| 3 | Seeks feedback from an expert outside school, found by the child or introduced by the school and known to it, and reports what they learned. | The educator knows who was approached and how, and sees the expert's feedback and the change it led to. | project · artefact | unafraid, capable | Reports the feedback without any change made. | asks-for-specific-feedback | R:E D:A E:A P:E → **edited** (chair) |  |
| 4 | States a standard for their work above the rubric's, and shows where the work meets it. | The educator reads a standard the rubric did not ask for and sees it met. | project · artefact | capable | Restates the rubric as their standard. | self-marks-against-a-rubric | R:A D:A E:A P:A → **accepted** |  |
| 5 | Learns an unfamiliar tool or topic from documentation or a course on their own, and demonstrates it. | The educator sees the tool used or the topic applied, not described. | project · observation note | capable, unafraid | Watches a tutorial and describes it without using the tool. | monitors-own-progress-on-the-map | R:A D:E E:E P:A → **edited** |  |
| 6 | Returns to a piece of work after a public setback, such as a lost debate or a failed demonstration, and improves it. | The educator sees the work taken up again and changed after the setback. | project · artefact | unafraid | Drops the piece after the setback. | persists-through-a-failed-attempt | R:A D:A E:A P:A → **accepted** |  |

## Creation & problem solving

*Observable at 16:* Turns ideas into experiments, prototypes, designs, investigations and useful outputs.


### Foundational · Nursery to Grade 2 · ages 3–8 · Discover

| # | Behaviour | What the educator sees | Where · how | Words | Not evidence when | Grows from | Council | Accept · Edit · Skip |
|---|---|---|---|---|---|---|---|---|
| 1 | Builds something with blocks or junk that matches a plan said aloud beforehand. | The educator hears the plan first and sees the build match it. | play · observation note · from age 4 | capable | Names what the finished pile is after building it. | — | R:A D:A E:A P:A → **accepted** |  |
| 2 | Solves a practical problem, such as a bridge that falls, by changing the materials or the design. | The educator sees the change made by the child and the bridge stand. | play · observation note · from age 4 | capable, unafraid | Asks an adult to fix the bridge. | — | R:A D:A E:A P:A → **accepted** |  |
| 3 | Draws a picture that shows an idea or a plan and explains what each part is. | The educator hears each part of the drawing named for what it does. | lesson · artefact · from age 4 | capable | Draws and says it is 'just a drawing'. | — | R:A D:A E:A P:A → **accepted** |  |
| 4 | Invents a new rule for a familiar game and plays a round with it. | The educator hears the rule proposed before play and sees it kept. | play · observation note · from age 5 | unafraid, capable | Proposes a new rule and then plays the round by the old rules. | — | R:E D:A E:A P:E → **edited** (chair) |  |
| 5 | Makes a second version of something made, and says what is different. | The educator sees two versions and hears the difference named. | play · artefact · from age 4 | capable | Makes the same thing again. | — | R:A D:A E:A P:A → **accepted** |  |
| 6 | Uses a simple tool, such as scissors, a hole punch or a magnifier, for its purpose without help. | The educator sees the tool used as intended with no hand over hand. | lesson · observation note · from age 4 | capable | Holds the tool and asks an adult to use it. | — | R:A D:A E:A P:A → **accepted** |  |
| 7 | Makes something for a particular person, such as a card or a model, and gives it to them saying who it is for. | The educator sees the thing handed over and hears who it is for. | play · observation note · from age 3 | kind, capable | Makes a card because the whole class was asked to make one. | — |  → **added** (chair) |  |
| 8 | Uses one object as another in pretend play, such as a block as a phone, and shows or tells what it stands for. | The educator sees the object used as something else and the child make plain, by word or action, what it is now. | play · observation note · from age 3 | capable, unafraid | Uses a toy phone as a phone. | — |  → **added** (chair) |  |

### Preparatory · Grades 3–5 · Investigate

| # | Behaviour | What the educator sees | Where · how | Words | Not evidence when | Grows from | Council | Accept · Edit · Skip |
|---|---|---|---|---|---|---|---|---|
| 1 | Makes a model or device that does what it was meant to do, such as a lever that lifts a load. | The educator sees the model do its job. | project · artefact | capable | Presents a model that looks right and does not work. | builds-something-from-a-plan-in-mind | R:A D:A E:A P:A → **accepted** |  |
| 2 | Tests a design, records what failed and changes one thing before testing again. | The educator sees the failure recorded and one change made. | project · artefact | capable, unafraid | Changes everything after a failure. | solves-a-practical-problem-with-materials | R:A D:A E:A P:A → **accepted** |  |
| 3 | Writes a materials list and a step plan before making something, and follows it. | The educator sees the list and plan written first and the make follow them. | project · artefact | capable | Writes the list after making. | draws-to-show-an-idea | R:A D:A E:A P:A → **accepted** |  |
| 4 | Writes an original story of their own with a beginning, a problem and an ending. | The educator reads a plot of the child's own with all three parts. | lesson · artefact | capable | Retells a known story with the names changed. | invents-a-rule-for-a-game | R:A D:A E:E P:A → **edited** |  |
| 5 | Presents a made thing to the class and says what changed from the first version and why. | The educator hears the change and its reason. | project · observation note | unafraid, capable | Shows the thing without saying what was changed. | makes-a-second-version | R:A D:E E:E P:A → **edited** |  |
| 6 | Chooses the right tool for a job from several available, and says why that one. | The educator hears the reason for the tool chosen. | project · observation note | capable | Uses whatever tool is nearest. | uses-a-tool-for-its-purpose | R:A D:A E:A P:A → **accepted** |  |

### Middle · Grades 6–8 · Apply

| # | Behaviour | What the educator sees | Where · how | Words | Not evidence when | Grows from | Council | Accept · Edit · Skip |
|---|---|---|---|---|---|---|---|---|
| 1 | Builds a prototype that meets a written brief with constraints, such as a budget or a size limit. | The educator checks the prototype against each constraint in the brief. | project · artefact | capable | Builds something impressive that ignores the constraints. | makes-a-model-that-works | R:A D:A E:A P:A → **accepted** |  |
| 2 | Keeps an iteration log across several tests with what changed and what the results were. | The educator reads several entries, each with a change and a result. | project · artefact | capable | Records the final version only. | tests-and-improves-a-design | R:A D:A E:A P:A → **accepted** |  |
| 3 | Fixes a program of their own when a test input breaks it, and shows the failing input and the change made. | The educator sees the input that broke the program and the line changed to fix it. | lesson · observation note | capable | Deletes the failing test input so the program passes. | chooses-a-tool-for-a-job | R:A D:S E:E P:A → **edited** (chair) |  |
| 4 | Produces a piece of art, media or performance for a real audience outside the class, such as younger children or parents. | The educator sees the piece reach the audience it was made for. | project · artefact | capable | Makes the piece for the class display only. | writes-an-original-story-or-poem | R:A D:A E:A P:A → **edited** (chair) |  |
| 5 | Pitches a solution to a problem and names one trade-off it makes. | The educator hears the trade-off named in the pitch. | project · observation note | unafraid, capable | Pitches the solution as having no downside. | presents-a-made-thing-and-what-changed | R:A D:E E:E P:A → **edited** |  |
| 6 | Carries out an investigation of an open question with a method they designed, and reports what was found. | The educator sees a method of the child's own and a finding, expected or not. | project · artefact | capable | Follows a worksheet method and reports the expected answer. | plans-a-make-with-a-list | R:A D:A E:A P:A → **accepted** |  |
| 7 | Makes or repairs something that someone in the school asked for, and hands it over working. | The educator sees the person who asked receive it and use it. | project · artefact | kind, capable | Makes something to a brief the educator set for marks. | makes-a-model-that-works |  → **added** (chair) |  |
| 8 | Makes an original artwork, composition or performance piece to a set theme and explains one choice made in it. | The educator sees the piece and hears one choice in it explained. | project · artefact | capable, unafraid | Copies a piece found online and explains the theme. | writes-an-original-story-or-poem |  → **added** (chair) |  |

### Secondary · Grades 9–10 · Create & Question

| # | Behaviour | What the educator sees | Where · how | Words | Not evidence when | Grows from | Council | Accept · Edit · Skip |
|---|---|---|---|---|---|---|---|---|
| 1 | Delivers a project to a brief from someone outside school and incorporates their feedback. | The educator sees the outside brief, the delivery and the feedback acted on. | project · artefact | capable | Delivers to their own brief. | builds-a-prototype-to-a-brief | R:A D:A E:A P:A → **accepted** |  |
| 2 | Documents a build or an experiment so another student repeats it without asking questions. | The educator sees another student repeat it from the document alone. | project · artefact | capable | Documents it so only they can repeat it. | runs-an-iteration-log | R:A D:A E:A P:A → **accepted** |  |
| 3 | Builds a piece of software with tests, and shows a test catching a bug. | The educator sees a test fail on a bug and pass after the fix. | project · artefact | capable | Shows working software with no tests. | codes-a-program-that-solves-a-task | R:A D:A E:A P:A → **accepted** |  |
| 4 | Finishes a piece of work to exhibition standard and labels it with what it is and what changed from the first version. | The educator sees the finished piece and its label naming the change from the first version. | project · artefact | unafraid, capable | Shows the first version with a label saying it is finished. | produces-a-piece-for-a-real-audience | R:A D:E E:E P:A → **edited** (chair) |  |
| 5 | Completes a real task in a school-arranged and supervised internship or apprenticeship placement, confirmed by the host. | The educator sees the host's confirmation of a task done, at a placement the school vetted and supervises. | project · artefact | capable | Attends the placement without a completed task. | pitches-a-solution-with-trade-offs | R:E D:A E:A P:A → **edited** |  |
| 6 | Designs and runs an original investigation, from question to method to findings, and presents it. | The educator sees the question, method and findings all the child's own. | project · artefact | capable | Repeats a textbook investigation. | investigates-an-open-question | R:A D:A E:A P:A → **accepted** |  |

**What the prompt could not do here (ADR 0018):**

- *stage unclear*: Secondary behaviours assume placements, exhibitions and outside briefs that the school has not yet defined; they should be read as what the programme must make possible.

## Communication & collaboration

*Observable at 16:* Writes, speaks, presents, listens, negotiates and contributes reliably to teams.


### Foundational · Nursery to Grade 2 · ages 3–8 · Discover

| # | Behaviour | What the educator sees | Where · how | Words | Not evidence when | Grows from | Council | Accept · Edit · Skip |
|---|---|---|---|---|---|---|---|---|
| 1 | Tells the circle something that happened, in two or more connected sentences in a language they speak, so that listeners can follow. | The educator hears two connected sentences about one piece of news, in whichever language the child uses, with no prompt between them. | circle · observation note · from age 3 | capable, unafraid | Says one word and stops when asked more. | — | R:E D:A E:E P:E → **edited** (chair) |  |
| 2 | Listens to a classmate and says something back about what they said. | The educator hears the response refer to the classmate's words. | circle · observation note · from age 4 | kind, capable | Waits for their own turn without responding. | — | R:A D:A E:A P:A → **accepted** |  |
| 3 | Asks to join a game, and accepts a no or joins in the way agreed. | The educator sees the ask and the answer respected. | play · observation note · from age 4 | kind, unafraid | Pushes into the game without asking. | — | R:A D:A E:A P:A → **accepted** |  |
| — | ~~Takes turns in a pair task, such as passing the crayon, without an adult managing it.~~ | ~~The educator sees the turns pass with no adult counting.~~ | play · observation note | kind | ~~Takes turns only when an adult counts.~~ | — | R:A D:A E:A P:A → **retired** (chair) |  |
| 4 | Shows a drawing or a build to the class and explains what it is. | The educator hears the explanation reach the class. | circle · observation note · from age 3 | unafraid, capable | Holds up the work silently. | — | R:A D:A E:A P:A → **accepted** |  |
| 5 | Uses words or signs to settle a dispute over a toy or a turn, such as proposing a swap. | The educator hears or sees the proposal made and sees the dispute end. | play · observation note · from age 4 | kind, unafraid | Repeats 'give it to me' louder until the other child gives in. | — | R:E D:A E:E P:E → **edited** (chair) |  |

### Preparatory · Grades 3–5 · Investigate

| # | Behaviour | What the educator sees | Where · how | Words | Not evidence when | Grows from | Council | Accept · Edit · Skip |
|---|---|---|---|---|---|---|---|---|
| 1 | Gives a two-minute prepared talk to the class with a beginning and an end. | The educator hears a shaped talk delivered to the room. | lesson · observation note | capable, unafraid | Reads the talk from the page without looking up. | tells-news-in-full-sentences | R:A D:A E:E P:A → **edited** |  |
| 2 | Adds to a classmate's idea in discussion, naming whose idea it builds on. | The educator hears the classmate credited and the idea extended. | lesson · observation note | kind, capable | Repeats the classmate's idea in other words without adding to it. | listens-and-responds-to-a-peer | R:A D:A E:A P:E → **edited** |  |
| 3 | Agrees roles with a group before a task starts and takes the role agreed. | The educator sees the roles agreed first and kept. | project · observation note | kind, capable | Takes the role they want and leaves the rest. | asks-to-join-and-accepts-no | R:A D:A E:A P:A → **accepted** |  |
| 4 | Writes a letter or message to a real person for a purpose, such as a request or a thank you. | The educator reads a named recipient and a clear purpose. | lesson · artefact | capable | Writes a letter to no one in particular. | tells-news-in-full-sentences | R:A D:A E:A P:A → **accepted** |  |
| 5 | Explains their method to a classmate who is stuck, without giving the answer. | The educator hears the method explained and the answer withheld. | practice · observation note | kind, capable | Tells the classmate the answer. | shows-work-and-explains-it | R:A D:A E:A P:A → **accepted** |  |
| 6 | Disagrees with a classmate's answer by giving a reason that addresses the answer, not the classmate, and lets the classmate reply. | The educator hears the disagreement and its reason addressed to the answer, not to the classmate, and the classmate given the floor. | lesson · observation note | unafraid, kind | Says 'you're wrong' without a reason. | uses-words-to-settle-a-dispute | R:E D:E E:A P:A → **edited** (chair) |  |

### Middle · Grades 6–8 · Apply

| # | Behaviour | What the educator sees | Where · how | Words | Not evidence when | Grows from | Council | Accept · Edit · Skip |
|---|---|---|---|---|---|---|---|---|
| 1 | Presents to an audience using a visual aid they made, and answers a question from the floor. | The educator sees the aid used and a question answered. | project · observation note | unafraid, capable | Reads slides aloud and takes no questions. | gives-a-short-prepared-talk | R:A D:A E:E P:A → **edited** |  |
| 2 | Leads a small-group discussion so that every member speaks, and summarises what was agreed. | The educator sees every member speak and hears the summary. | project · observation note | kind, capable | Speaks most and summarises their own view. | builds-on-a-peer-idea | R:A D:A E:A P:A → **accepted** |  |
| 3 | Resolves a disagreement in a group task by proposing an option both sides accept. | The educator sees the option proposed and both sides carry on. | project · observation note | kind, unafraid | Gives way to the louder side so that the task can go on. | negotiates-roles-in-a-group | R:E D:A E:A P:A → **edited** |  |
| 4 | Writes a piece in a tone suited to a named audience, such as a report for the head or a guide for Grade 3. | The educator reads a tone that fits the audience named. | lesson · artefact | capable | Writes in the same tone for every audience. | writes-a-letter-for-a-purpose | R:A D:A E:A P:E → **edited** |  |
| 5 | Gives a classmate written feedback with one strength and one specific change to make. | The educator reads a strength and a change the classmate could act on. | lesson · artefact | kind, capable | Writes 'good job' or 'needs work'. | explains-a-method-to-a-peer | R:A D:A E:A P:A → **accepted** |  |
| 6 | Argues the side assigned to them in a structured debate, using evidence for it, whichever side that is. | The educator hears evidence used for the assigned side and notes that the side was assigned. | lesson · observation note | unafraid, capable | Argues the assigned side with opinions and no evidence. | disagrees-politely-with-a-reason | R:E D:E E:A P:E → **edited** (chair) |  |

### Secondary · Grades 9–10 · Create & Question

| # | Behaviour | What the educator sees | Where · how | Words | Not evidence when | Grows from | Council | Accept · Edit · Skip |
|---|---|---|---|---|---|---|---|---|
| 1 | Presents work to an audience outside school, such as parents, a partner organisation or a competition panel, and handles questions. | The educator sees the outside audience and questions handled. | project · video clip | unafraid, capable | Presents only to classmates. | presents-with-a-visual-aid | R:A D:A E:A P:A → **accepted** |  |
| 2 | Runs a meeting with an agenda and leaves it with actions assigned to named people. | The educator reads the agenda and the actions with names. | project · artefact | capable, kind | Holds a meeting with no record of what was decided. | leads-a-discussion-fairly | R:A D:A E:A P:A → **accepted** |  |
| 3 | Negotiates an outcome with adults, such as a change to a school routine, presenting a case and reaching an agreed outcome with them. | The educator sees the case made, the adults' response answered, and an outcome both sides state as agreed. | project · observation note | unafraid, capable | Complains about the routine without proposing a case. | resolves-a-group-conflict-by-agreement | R:E D:A E:A P:A → **edited** |  |
| 4 | Writes a formal document, such as a proposal, a report or an application, that a stranger could act on. | The educator gives the document to someone uninvolved and sees them act on it. | project · artefact | capable | Writes a document that needs the author present to explain it. | writes-for-a-named-audience | R:A D:A E:A P:A → **accepted** |  |
| 5 | Runs a mentoring session with a younger student, in a pairing the school set up, and adds it to a log of earlier dated sessions. | The educator sees the session take place and the log with earlier dated entries, kept without the younger child's name or difficulties. | project · artefact | kind, capable | Logs a first meeting as mentoring. | gives-usable-peer-feedback | R:E D:E E:A P:A → **edited** (chair) |  |
| 6 | Restates an opposing view to its holder's satisfaction before answering it, in a discussion. | The educator hears the holder agree the restatement is fair. | lesson · observation note | kind, unafraid, capable | Answers an opposing view without restating it. | argues-a-side-in-a-debate | R:A D:A E:A P:A → **accepted** |  |

**What the prompt could not do here (ADR 0018):**

- *other*: Word tags follow the draft meanings of capable, kind and unafraid in the proposal; if the founders' meanings differ, the tags should be re-read against them.

## Technology & AI

*Observable at 16:* Uses digital tools productively; verifies AI outputs; understands bias, privacy, provenance and limitations.


### Foundational · Nursery to Grade 2 · ages 3–8 · Discover

| # | Behaviour | What the educator sees | Where · how | Words | Not evidence when | Grows from | Council | Accept · Edit · Skip |
|---|---|---|---|---|---|---|---|---|
| 1 | Operates a simple screen-free device, such as a story player or a torch, for a stated purpose, with an adult present. | The educator sees the device used for the purpose the child stated and put down afterwards. | lesson · observation note · from age 3 | capable | Taps a device at random. | — | R:A D:A E:E P:E → **edited** (chair) |  |
| 2 | Follows a three-step sequence of instructions, given in a language they understand, in order, such as in a coding game played without a screen. | The educator gives the steps in a language the child understands and sees the three done in the order given. | play · observation note · from age 4 | capable | Does the steps in a different order. | — | R:E D:A E:A P:E → **edited** (chair) |  |
| 3 | Gives a classmate step-by-step instructions to move across a grid, and corrects one wrong step. | The educator hears the steps and sees one corrected. | play · observation note · from age 5 | capable | Says 'go there' and points. | — | R:A D:A E:A P:E → **edited** |  |
| 4 | Says whether a picture or a story is real or made up, and gives one reason. | The educator hears the judgement and a reason for it. | circle · observation note · from age 5 | capable | Says real or pretend without a reason. | — | R:A D:A E:E P:A → **edited** |  |
| 5 | Asks before using a classmate's crayons, drawing or belongings. | The educator hears the ask before the crayons or the drawing are touched. | play · observation note · from age 3 | kind | Asks only after already picking the thing up. | — | R:A D:A E:E P:E → **edited** |  |
| — | ~~Carries and puts away a shared device carefully, as shown.~~ | ~~The educator sees the device carried with two hands and returned to its place.~~ | lesson · observation note | kind, capable | ~~Drops or leaves the device on the floor.~~ | — | R:E D:A E:S P:A → **retired** (chair) |  |

### Preparatory · Grades 3–5 · Investigate

| # | Behaviour | What the educator sees | Where · how | Words | Not evidence when | Grows from | Council | Accept · Edit · Skip |
|---|---|---|---|---|---|---|---|---|
| 1 | Uses a digital tool to produce a piece of work, such as a typed paragraph or a chart from data they collected. | The educator sees the finished piece made with the tool. | lesson · artefact | capable | Uses the tool to play during work time. | operates-a-simple-device-for-a-purpose | R:A D:A E:A P:A → **accepted** |  |
| 2 | Writes a short block-based program and fixes it when it does not do what was intended. | The educator sees the program misbehave and the child change it until it works. | lesson · artefact | capable | Runs a sample program without changing it. | follows-a-sequence-of-instructions | R:A D:A E:A P:A → **accepted** |  |
| 3 | Explains in plain words what a short set of instructions or program will do before running it. | The educator hears the prediction before the run. | lesson · observation note | capable | Runs it and then describes what happened. | gives-instructions-to-move-a-friend | R:A D:A E:A P:A → **accepted** |  |
| 4 | Checks an answer from a search or an AI tool against a book or a second source before using it. | The educator sees the second source opened before the answer is used. | lesson · observation note | capable | Copies the first answer given. | sorts-real-from-pretend | R:A D:A E:A P:A → **accepted** |  |
| 5 | Says what should not be shared online, such as full name, address or school, and applies it in a task. | The educator sees the private fields left out in the task. | lesson · observation note | capable | Types their full name and address into a form without asking. | asks-before-using-someone-elses-thing | R:A D:A E:A P:A → **accepted** |  |
| 6 | Names where an image or fact came from when using it in their work. | The educator sees the source named beside the image or fact. | lesson · artefact | capable, kind | Uses an image with no source. | asks-before-using-someone-elses-thing | R:A D:A E:A P:A → **accepted** |  |
| 7 | Writes or dictates step-by-step instructions for a classmate to draw a figure, then changes a step when the drawing does not match what was meant. | The educator sees the steps, the drawing they produced and the step rewritten after it; the filed artefact is the child's own instruction sheet, not the classmate's drawing. | lesson · artefact | capable | Draws the figure for the classmate instead of rewriting the step. | gives-instructions-to-move-a-friend |  → **added** (chair) |  |

### Middle · Grades 6–8 · Apply

| # | Behaviour | What the educator sees | Where · how | Words | Not evidence when | Grows from | Council | Accept · Edit · Skip |
|---|---|---|---|---|---|---|---|---|
| 1 | Chooses a digital tool suited to a task, such as a spreadsheet for data, and justifies the choice. | The educator hears the justification and sees the tool fit. | project · observation note | capable | Uses the same tool for everything. | uses-a-tool-to-produce-work | R:A D:A E:A P:A → **accepted** |  |
| 2 | Writes a text-based program with a loop and a condition that solves a set problem. | The educator sees the loop and condition in the code and the problem solved. | lesson · artefact | capable | Writes straight-line code with no loop. | writes-and-debugs-a-short-program | R:A D:A E:A P:A → **accepted** |  |
| 3 | Checks an AI tool's output claim by claim against a source, marking each claim confirmed or corrected and naming the source used. | The educator sees each claim marked confirmed or corrected and the source used written beside the marks. | lesson · artefact | capable, unafraid | Marks every claim confirmed without opening a source. | checks-an-ai-or-search-answer | R:A D:E E:E P:A → **edited** (chair) |  |
| 4 | Explains, with an example, how an app's recommendation or an AI answer can be biased by its data. | The educator hears a concrete example, not a slogan. | lesson · observation note | capable | Says 'AI is biased' without an example. | explains-what-an-algorithm-does | R:A D:A E:A P:A → **accepted** |  |
| 5 | Sets privacy settings on a school account as taught and explains what each setting protects. | The educator sees the settings set and hears each one explained. | lesson · observation note | capable | Leaves defaults and cannot say what they do. | keeps-personal-details-private-online | R:A D:A E:A P:A → **accepted** |  |
| 6 | States where AI was used in their work and where it was not, when handing it in. | The educator reads the attribution on the submitted work. | lesson · artefact | unafraid, capable | Writes 'used AI' on the cover sheet with no indication of where. | credits-a-source-for-an-image-or-fact | R:A D:A E:A P:E → **edited** |  |

### Secondary · Grades 9–10 · Create & Question

| # | Behaviour | What the educator sees | Where · how | Words | Not evidence when | Grows from | Council | Accept · Edit · Skip |
|---|---|---|---|---|---|---|---|---|
| 1 | Builds a working digital product, such as a website, app or automation, for a real user, and gets their feedback. | The educator sees the user use it and the feedback recorded. | project · artefact | capable | Builds a demo no one uses. | chooses-the-right-tool-for-a-task | R:A D:E E:E P:A → **edited** |  |
| 2 | Writes a program that reads real data, uses a ready-made code library, and produces a checked result. | The educator sees the check that the result is right. | project · artefact | capable | Produces output with no check that it is right. | writes-a-text-program-with-a-loop-and-a-condition | R:A D:A E:A P:E → **edited** |  |
| 3 | Uses AI in a piece of work with a log of prompts, what was kept, what was rejected and why. | The educator reads the log beside the work. | project · artefact | capable, unafraid | Keeps the prompts but not what was rejected or why. | verifies-an-ai-output-and-finds-an-error | R:A D:A E:A P:E → **edited** |  |
| 4 | Evaluates a technology's benefits and harms for a named group, with evidence, and takes a position. | The educator reads the weighing and the position taken. | lesson · artefact | capable, kind | Lists benefits and harms without weighing them. | explains-how-a-recommendation-or-bias-arises | R:A D:A E:A P:A → **accepted** |  |
| 5 | Completes a task without AI that they could have done with it, and writes two lines on what doing it alone showed. | The educator sees the task done unaided and reads the two lines beneath it. | lesson · artefact | unafraid, capable | Does the task unaided because AI was not allowed, and says nothing about what it showed. | attributes-ai-help-in-own-work | R:A D:E E:A P:E → **edited** |  |
| 6 | Handles other people's data in a project according to a stated rule, such as consent and deletion, and shows the rule was followed. | The educator sees the rule stated and evidence it was kept. | project · artefact | kind, capable | States a consent rule at the start and keeps the data after the project ends. | manages-own-privacy-settings | R:A D:A E:A P:E → **edited** |  |

**What the prompt could not do here (ADR 0018):**

- *no observable form*: Below Grade 4 the school puts no screen in front of a child, so the Foundational behaviours are unplugged proxies: sequencing, giving instructions, real versus pretend, care of a shared device.

## Self & relationships

*Observable at 16:* Shows resilience, emotional regulation, physical competence, empathy and responsible independence.


### Foundational · Nursery to Grade 2 · ages 3–8 · Discover

| # | Behaviour | What the educator sees | Where · how | Words | Not evidence when | Grows from | Council | Accept · Edit · Skip |
|---|---|---|---|---|---|---|---|---|
| 1 | Names what they feel after a fall, a dispute or a lost game, in their own words, and chooses what to do next. | The educator hears a feeling named in the child's own words and sees the choice made; the note records the choice, never the words or the cause. | circle · observation note · from age 4 | unafraid, capable | Is told by an adult what they are feeling and repeats it. | — | R:E D:E E:E P:E → **edited** (chair) |  |
| 2 | Waits for a turn on the slide or with a toy without a reminder from an adult. | The educator sees the wait with no adult prompt. | play · observation note · from age 4 | kind | Waits only after an adult says their name. | — | R:A D:A E:A P:A → **accepted** |  |
| 3 | Notices a classmate who is hurt or crying and does something for them, such as fetching an adult or sitting with them. | The educator sees the noticing and the act that follows. | play · observation note · from age 3 | kind | Joins the crowd around the hurt classmate to look, without doing anything for them. | — | R:E D:E E:E P:E → **edited** (chair) |  |
| 4 | Manages their own bag, bottle and shoes at arrival and departure without an adult doing it for them, using any aids they have. | The educator sees the bag, bottle and shoes handled by the child, with their own aids if any, and no adult's hands on them. | circle · observation note · from age 4 | capable | Holds out a foot for an adult to put the shoe on. | — | R:E D:A E:A P:E → **edited** (chair) |  |
| — | ~~Runs, jumps with two feet together and balances on one foot for a count of three during play.~~ | ~~The educator sees each movement done without a hand held.~~ | outdoors · video clip | capable | ~~Does the movement only with a hand held.~~ | — | R:S D:E E:E P:E → **retired** (R1) |  |
| 5 | Returns to play after a small hurt or a lost game, once looked after. | The educator sees the child back in play in the same session. | outdoors · observation note · from age 3 | unafraid | Returns to play only when an adult walks them back to the game. | — | R:E D:A E:A P:A → **edited** |  |
| 6 | Takes a full turn in an outdoor running or climbing game, moving in the way their own body moves. | The educator sees the child take the turn from start to finish, with any aid they use. | outdoors · observation note · from age 3 | capable, unafraid | Runs onto the field with the others and stands watching them take the turn. | — |  → **added** (chair) |  |
| 7 | Tells a classmate 'stop' or 'I am still using it', in words or signs, when the classmate reaches for or takes what they are using. | The educator hears or sees the words or sign given to the classmate before any adult steps in; the note holds the child's words, never the incident or the classmate. | play · observation note · from age 3 | unafraid | Says 'stop' only after the educator has told the classmate to stop. | — |  → **added** (chair) |  |

### Preparatory · Grades 3–5 · Investigate

| # | Behaviour | What the educator sees | Where · how | Words | Not evidence when | Grows from | Council | Accept · Edit · Skip |
|---|---|---|---|---|---|---|---|---|
| 1 | Uses a strategy learned in class, such as breathing or stepping away, before responding in a conflict. | The educator sees the strategy used in the moment, before the response, and notes the strategy alone, not the conflict or who else was in it. | play · observation note | capable, kind | Names the strategy afterwards but did not use it. | says-what-they-are-feeling-and-chooses | R:E D:A E:A P:A → **edited** |  |
| 2 | Keeps an agreement made with a classmate, such as a swap or a promise, without an adult enforcing it. | The educator sees the agreement honoured with no adult involved. | play · observation note | kind | Keeps the agreement only when reminded. | waits-for-a-turn-without-a-reminder | R:A D:A E:A P:A → **accepted** |  |
| 3 | Invites a child standing alone at the edge of a game or group to join, before any adult suggests it. | The educator sees the child alone at the edge and the invitation come from the classmate first. | play · observation note | kind, unafraid | Invites the child when an adult asks the group to. | comforts-a-classmate | R:A D:E E:A P:A → **edited** |  |
| 4 | Does their class responsibility, such as watering the plants, on a day when nobody reminded them, using their own way of remembering. | The educator sees the job done before anyone has mentioned it that day, whatever memory aid the child uses. | lesson · observation note | capable, kind | Does the job after the educator glances at the job chart. | manages-own-things | R:E D:E E:E P:A → **edited** (chair) |  |
| 5 | Shows a physical skill, such as skipping or catching, that an earlier record shows they could not yet do. | The educator sees the skill done unaided and finds the earlier note saying the child could not yet do it. | outdoors · observation note | capable, unafraid | Shows a skill they arrived at school already able to do. | takes-a-full-turn-in-an-outdoor-game | R:E D:E E:E P:E → **edited** (chair) |  |
| 6 | Accepts losing a game or a contest and congratulates the winner. | The educator hears the congratulation given to the winner. | play · observation note | kind, unafraid | Shakes the winner's hand only when an adult tells the players to. | returns-to-play-after-a-small-hurt | R:A D:A E:A P:E → **edited** |  |

### Middle · Grades 6–8 · Apply

| # | Behaviour | What the educator sees | Where · how | Words | Not evidence when | Grows from | Council | Accept · Edit · Skip |
|---|---|---|---|---|---|---|---|---|
| 1 | Goes back to a classmate after a conflict to apologise or to sort it out, without being sent. | The educator sees the approach made unprompted and notes the repair alone, not the conflict or the classmate. | project · observation note | kind, unafraid | Apologises when the educator stands beside them and waits for it. | uses-a-strategy-before-acting | R:E D:E E:A P:A → **edited** (chair) |  |
| 2 | Delivers their agreed part to a team, such as attending a practice or handing in a section, on the date the team set. | The educator sees the team's plan with the date and the part delivered on it. | project · observation note | kind, capable | Attends the sessions but leaves their part for others to deliver. | keeps-an-agreement-made-with-a-classmate | R:E D:E E:E P:E → **edited** (chair) |  |
| 3 | Speaks up when a classmate is being excluded or mocked, in the moment. | The educator hears the intervention as it happens and notes the speaking up alone; the mocking itself goes to the school's own process, not this record. | play · observation note | kind, unafraid | Joins the classmate's side once an adult has already stepped in. | includes-a-child-left-out | R:E D:A E:A P:E → **edited** (chair) |  |
| 4 | Hands in a piece of work on its due date with the deadline written in their own planner the week before. | The educator sees the planner entry dated at least a week earlier and the work in on the day. | lesson · artefact | capable | Hands work in on time with a planner filled in that morning. | carries-out-a-class-responsibility | R:A D:E E:A P:A → **edited** |  |
| 5 | Shows a training record for a goal about what they can do, such as a distance, with attempts dated across four or more weeks. | The educator reads the goal and attempt entries spanning four or more weeks, a record of what was done, never a body measure. | outdoors · artefact | capable, unafraid | Records one attempt on the last day. | learns-a-new-physical-skill-through-practice | R:E D:E E:A P:A → **edited** (chair) |  |
| — | ~~Asks a trusted adult for help with a personal difficulty before it affects their work.~~ | ~~The adult approached records that the ask came before any missed work.~~ | lesson · observation note | unafraid | ~~Mentions the difficulty only after a missed deadline.~~ | accepts-a-loss-and-congratulates | R:S D:S E:S P:S → **retired** (R1) |  |
| 6 | Tells the educator before a deadline that a piece of work will be late and proposes a new date. | The educator hears it before the date, with a new date offered. | lesson · observation note | unafraid, capable | Explains why the work is late after the deadline has passed. | keeps-an-agreement-made-with-a-classmate |  → **added** (chair) |  |
| 7 | Takes on part of a classmate's share of a team task after the classmate says they cannot finish it, and tells the team. | The educator hears the classmate say so, sees the extra part done and hears the team told; the note names the part taken on, not the classmate or why. | project · observation note | kind | Does the whole task alone without telling the team. | includes-a-child-left-out |  → **added** (chair) |  |

### Secondary · Grades 9–10 · Create & Question

| # | Behaviour | What the educator sees | Where · how | Words | Not evidence when | Grows from | Council | Accept · Edit · Skip |
|---|---|---|---|---|---|---|---|---|
| 1 | Mediates between two classmates in conflict so that both agree a way forward. | The educator sees both classmates accept the way forward and notes the mediation alone, not the dispute or who was in it. | project · observation note | kind, capable | Takes one side. | repairs-a-relationship-after-a-conflict | R:E D:A E:A P:A → **edited** |  |
| 2 | Leads a team through a setback, such as a failed event, by re-planning with the team. | The educator sees the re-plan made with the team present. | project · observation note | unafraid, kind, capable | Assigns blame and re-plans alone. | keeps-a-commitment-to-a-team | R:A D:A E:A P:A → **accepted** |  |
| 3 | Raises an unfairness affecting others through a school channel, such as council, and follows it through. | The educator sees the matter raised in the channel and followed up, and notes the raising, not the complaint's content; a concern about an adult goes to the safeguarding lead instead. | project · artefact | kind, unafraid | Complains privately and lets it drop. | speaks-up-for-a-classmate | R:E D:A E:A P:A → **edited** |  |
| 4 | Shows a term plan that holds both exam preparation and a project, with a dated change made after something slipped. | The educator reads the plan, the dated change and what prompted it. | lesson · artefact | capable | Shows a plan written after the term ended. | manages-own-schedule-for-a-week | R:A D:E E:A P:A → **edited** |  |
| 5 | Brings their own dated record of a physical practice kept across the year and names one change in it. | The educator sees the child's own dated record and hears one change named from it. | outdoors · artefact | capable | Speaks about the practice in general terms with no record to show. | trains-for-a-physical-goal | R:A D:E E:E P:A → **edited** |  |
| — | ~~Supports a peer through a difficulty over time and knows when to bring in an adult.~~ | ~~The educator learns of the support from the peer or sees the adult brought in at the right time.~~ | project · observation note | kind, capable | ~~Keeps a peer's serious difficulty secret from every adult.~~ | asks-a-trusted-adult-for-help | R:S D:E E:S P:S → **retired** (R1) |  |
| 6 | Brings a classmate who missed a session up to date on what was agreed and what they missed, without being asked. | The educator sees the catch-up happen before the next session, unprompted. | project · observation note | kind, capable | Forwards the notes when the classmate asks for them. | takes-on-part-of-a-classmates-share |  → **added** (chair) |  |
| 7 | Stops an argument that has reached raised voices by proposing a break and a time to return to it. | The educator hears the break proposed with a time to return and sees the argument pause; the note holds the proposal, not the argument or who was in it. | project · observation note | kind, capable | Walks away from the argument without a word about returning. | repairs-a-relationship-after-a-conflict |  → **added** (chair) |  |

**What the prompt could not do here (ADR 0018):**

- *other*: Emotional regulation is written only as actions a person could see; the regulation itself is not observable. The physical behaviours are placeholders for a movement checklist the school should adopt, such as TGMD-style criteria, which this prompt cannot author.

## Society, ethics & planet

*Observable at 16:* Can examine trade-offs, understand systems and consider consequences beyond the self.


### Foundational · Nursery to Grade 2 · ages 3–8 · Discover

| # | Behaviour | What the educator sees | Where · how | Words | Not evidence when | Grows from | Council | Accept · Edit · Skip |
|---|---|---|---|---|---|---|---|---|
| 1 | Waters a plant or feeds the class animal on their day, and checks it is alright. | The educator sees the care given and the check made. | outdoors · observation note · from age 4 | kind, capable | Waters it when an adult hands over the can. | — | R:A D:A E:A P:A → **accepted** |  |
| 2 | Puts waste into the right bin, wet, dry or paper, without prompting. | The educator watches the bins after snack and sees the right one chosen with nobody pointing. | play · observation note · from age 4 | kind | Puts waste in the nearest bin. | — | R:A D:A E:E P:A → **edited** |  |
| 3 | Shares a material, such as crayons or blocks, with a classmate who has none, without being asked. | The educator sees the share come from the child. | play · observation note · from age 3 | kind | Shares after an adult says 'share'. | — | R:E D:A E:A P:A → **edited** |  |
| — | ~~Notices that a classmate or a younger child needs something and gets it for them.~~ | ~~The educator sees the need met without an adult pointing it out.~~ | play · observation note | kind | ~~Notices and tells an adult only when asked.~~ | — | R:A D:E E:S P:A → **retired** (chair) |  |
| 4 | Says what would be fair for everyone when a share or a turn is in dispute, including a child who is not their friend. | The educator hears a fairness that applies to everyone, including a child the speaker was not playing with. | play · observation note · from age 5 | kind, unafraid | Says fair means getting their own way. | — | R:E D:A E:E P:A → **edited** (chair) |  |
| — | ~~Leaves a shared space, such as the reading corner, tidy for the next group.~~ | ~~The educator sees the space left ready.~~ | circle · observation note | kind | ~~Tidies only their own spot.~~ | — | R:A D:A E:S P:A → **retired** (chair) |  |
| 5 | Turns off a tap left running or a light left on in an empty room, with nobody asking. | The educator sees the tap or switch closed by the child before anyone speaks. | play · observation note · from age 4 | kind, capable | Turns it off when the educator points at it. | — |  → **added** (chair) |  |
| 6 | Picks up litter that is not their own from the playground and puts it in the bin. | The educator sees litter picked up that the child did not drop. | outdoors · observation note · from age 3 | kind | Puts their own wrapper in the bin. | — |  → **added** (chair) |  |
| 7 | Votes in a class choice and goes along with the result when their choice loses. | The educator sees the vote cast and the child join the chosen activity after their choice lost. | circle · observation note · from age 4 | kind, unafraid | Joins the winning activity having voted for it. | — |  → **added** (chair) |  |
| 8 | Handles a living thing found outdoors, such as a snail or a worm, gently and puts it back where it was. | The educator sees the creature handled without harm and returned to its place. | outdoors · observation note · from age 3 | kind | Keeps the creature in a box to show the class later. | — |  → **added** (chair) |  |

### Preparatory · Grades 3–5 · Investigate

| # | Behaviour | What the educator sees | Where · how | Words | Not evidence when | Grows from | Council | Accept · Edit · Skip |
|---|---|---|---|---|---|---|---|---|
| 1 | Reports a figure they measured about the school's use of water, paper or power, and says how they measured it. | The educator hears the figure, what it is about, and how it was measured. | outdoors · artefact | capable | Reports a figure found online about schools in general. | cares-for-a-plant-or-animal | R:A D:A E:A P:A → **edited** (chair) |  |
| 2 | Proposes and carries out one way to reduce waste in a class activity and checks whether it worked. | The educator sees the change made and the check afterwards. | project · artefact | kind, capable | Proposes a way and does not try it. | sorts-waste-into-the-right-bin | R:A D:A E:A P:A → **accepted** |  |
| 3 | Explains a school or class rule by the reason for it, not just 'because it is the rule'. | The educator hears the reason, not the rule repeated. | circle · observation note | capable | Says the rule is the rule. | says-what-is-fair-in-a-game | R:A D:A E:A P:A → **accepted** |  |
| 4 | Names who else is affected by a decision in a story or a class choice, beyond themselves. | The educator hears others named and how they are affected. | lesson · observation note | kind, capable | Names only how it affects them. | shares-without-being-asked | R:A D:A E:A P:A → **accepted** |  |
| 5 | Does a task that helps someone outside the class, such as reading to younger children, and reports it. | The educator sees the task done and the report. | project · artefact | kind | Helps a classmate inside the class and reports it as service. | shares-without-being-asked | R:A D:A E:A P:E → **edited** |  |
| — | ~~Keeps a promise made to the group, such as bringing materials, and says so if it cannot be kept.~~ | ~~The educator sees the promise kept, or hears it explained in time.~~ | project · observation note | kind, unafraid | ~~Forgets the promise and says nothing.~~ | keeps-a-shared-space-tidy | R:E D:A E:A P:A → **retired** (chair) |  |

### Middle · Grades 6–8 · Apply

| # | Behaviour | What the educator sees | Where · how | Words | Not evidence when | Grows from | Council | Accept · Edit · Skip |
|---|---|---|---|---|---|---|---|---|
| 1 | Collects data on a local issue, such as traffic or water at school, and presents the findings to those who can act on them. | The educator sees the findings presented to a person or body who can act on the issue, not only to the class. | project · artefact | capable | Presents the findings to the class only, with no one who could act on them in the room. | measures-something-about-the-campus | R:A D:A E:A P:E → **edited** (chair) |  |
| 2 | Sets out both sides of a real decision, such as cost against waste, before recommending one, and names who bears the cost. | The educator reads both sides set out and the person or group who bears the cost named. | project · artefact | capable, kind | Recommends the option with no downside named. | reduces-waste-in-a-class-project | R:A D:A E:A P:A → **edited** (chair) |  |
| 3 | States the strongest case for each side of a civic question before giving their own view. | The educator hears each side made well before the child's view, and notes the two cases made, not the view the child gave. | lesson · observation note | capable, unafraid | Gives their own view and a token version of the other side. | explains-a-rule-by-its-reason | R:E D:E E:E P:A → **edited** |  |
| 4 | Changes a plan after seeing that it would harm someone else, and says why. | The educator sees the change and hears the reason. | project · observation note | kind, unafraid | Keeps the plan and apologises later. | considers-who-else-is-affected | R:A D:A E:A P:A → **accepted** |  |
| 5 | Organises a service activity with classmates, from plan to delivery, for people outside school. | The educator sees the plan and the delivery, with the people served described and not photographed or named. | project · artefact | kind, capable | Joins a service activity organised by adults. | does-a-service-task-outside-the-class | R:E D:A E:A P:A → **edited** |  |
| 6 | Owns a mistake that affected others, tells those affected and puts it right. | The educator sees those affected told and the repair made, and notes the owning and the repair, not the mistake's detail or who was affected. | project · observation note | unafraid, kind | Puts it right quietly without telling those affected. | considers-who-else-is-affected | R:E D:A E:A P:A → **edited** |  |

### Secondary · Grades 9–10 · Create & Question

| # | Behaviour | What the educator sees | Where · how | Words | Not evidence when | Grows from | Council | Accept · Edit · Skip |
|---|---|---|---|---|---|---|---|---|
| 1 | Models a system, such as the school's water or a market, with its feedback loops, and uses it to explain an outcome. | The educator sees feedback loops in the model and an outcome explained by them. | project · artefact | capable | Draws a diagram with arrows and no feedback. | investigates-a-local-issue-with-data | R:A D:A E:A P:A → **accepted** |  |
| 2 | Applies an ethical framework to a real dilemma, names the trade-offs, decides and defends it. | The educator reads the framework applied, the trade-offs and the defence. | lesson · artefact | capable, kind | Decides on instinct and adds a framework label. | weighs-a-trade-off-in-a-real-decision | R:A D:A E:A P:A → **accepted** |  |
| 3 | Engages a public body, business or community group on an issue through the school, with a documented exchange. | The educator sees the exchange documented, sent through the school and carrying no home address or personal details of the child. | project · artefact | unafraid, capable | Writes a letter that is never sent. | argues-both-sides-of-a-civic-question | R:E D:A E:A P:A → **edited** |  |
| 4 | Changes something they do at school, such as printing or single-use packaging, after seeing evidence of its harm, and names the evidence. | The educator sees the changed practice at school and hears the evidence named. | project · observation note | kind, unafraid | Pledges the change publicly and shows a log begun the day before. | changes-a-plan-that-would-harm-others | R:E D:E E:S P:E → **edited** (chair) |  |
| 5 | Presents the term's record of a service commitment they led, showing what changed for the people served. | The educator reads dated entries across the term and a stated change for those served, written without their names or private circumstances. | project · artefact | kind, capable | Runs a one-day event and reports it as sustained. | organises-a-service-activity | R:E D:E E:A P:A → **edited** (chair) |  |
| 6 | Holds a public role in the school, such as council or event lead, and accounts for decisions to those affected. | The educator sees the accounting made to those affected. | project · observation note | unafraid, capable, kind | Holds the role and reports to adults only. | owns-a-mistake-that-affected-others | R:A D:A E:A P:A → **accepted** |  |

**What the prompt could not do here (ADR 0018):**

- *capability too broad*: At the Foundational stage 'consequences beyond the self' can only show as sharing, tidying and care, which overlap with kind behaviours under self-and-relationships; the founders may merge or move them.

---

*204 live behaviours in 32 cells. The machine copy is `docs/school-os-level2-behaviours-draft.json`; the operations coordinator transcribes the sitting's decisions into it, and the validator re-runs on the result.*
