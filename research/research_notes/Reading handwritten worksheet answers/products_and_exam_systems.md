# How production products and exam systems read and mark handwritten answers on paper

Scope note: researched 21-Sep-2026. Some official help centres (Gradescope Guides, Crowdmark Help, CBSE FAQ PDF, GradeCam partner pages) returned HTTP 403 to the fetch tool. For those, facts come from search-engine snippets of the official pages. Each such case is marked "(snippet)". Everything else was read in full, including the arXiv papers and PDFs, which were converted to text and checked line by line.

---

## Q1. Gradescope (Turnitin): how answer regions are defined, how submissions are aligned, what AI does, and how much is automated

### Takeaway
Gradescope depends entirely on known template geometry. The instructor uploads the blank worksheet PDF and draws a box for each question. Every scan is then compared with that template. The AI reads only short answers written on one line (multiple choice, math fill-in-the-blank, text fill-in-the-blank). It uses them to suggest groups of identical answers. A human confirms each group and grades the group once. Gradescope does not auto-assign marks from handwriting, and it publishes no accuracy figure for its handwriting reading.

### Cited Findings
**Original system (2017 paper, older but still the core design):**
- The instructor uploads "a blank PDF of the exam" as a template. The assignment outline is a list of questions, each with a point value and "the region on the template that corresponds to each question". Instructors "select the regions by drawing boxes on the exam". They also draw a box around the name area. — [Singh et al., L@S 2017](https://people.eecs.berkeley.edu/~pabbeel/papers/2017-LaS-gradescope.pdf)
- Two assignment types are supported. The first is "worksheet-style, fixed-length" (every student writes on the template and submits the same pages). The second is variable-length (arbitrary pages). The template/region workflow is built for the fixed-length type. — [Singh et al. 2017](https://people.eecs.berkeley.edu/~pabbeel/papers/2017-LaS-gradescope.pdf)
- A design constraint: "exams did not need to be altered in order to be graded online". The paper contrasts this with systems that need "bubble sections, QR codes". — [Singh et al. 2017](https://people.eecs.berkeley.edu/~pabbeel/papers/2017-LaS-gradescope.pdf)
- Batch scanning: the system "automatically suggests how to split the batch into individual exams". The user confirms the split or merges/reorders pages. — [Singh et al. 2017](https://people.eecs.berkeley.edu/~pabbeel/papers/2017-LaS-gradescope.pdf)
- Name assignment was deliberately left manual: "We make the name assignment step fast, without automating it. This leads to a far lower error rate in name assignment than that shown by some of the automated systems." The UI shows only the name crop and autocompletes from the roster. — [Singh et al. 2017](https://people.eecs.berkeley.edu/~pabbeel/papers/2017-LaS-gradescope.pdf)
- Grading shows one student's answer to one question at a time, with a rubric the grader builds while marking. Changing a rubric item re-applies to every student already graded. Graders focus on a single question across all students. — [Singh et al. 2017](https://people.eecs.berkeley.edu/~pabbeel/papers/2017-LaS-gradescope.pdf)
- Measured result: time per student answer "rapidly decays with number of answers graded". The sample was 100 CS courses, 596 assignments and 7,710 questions. The median assignment had 14 questions and 141 submissions, and took 14.6 person-hours to grade. Rubrics averaged 5.6 items (median 5). Scale at the time: over 10 million pages from 200 institutions over 4 years. — [Singh et al. 2017](https://people.eecs.berkeley.edu/~pabbeel/papers/2017-LaS-gradescope.pdf)
- The time savings in the paper come from instructor surveys (Table 7). The paper does not report a controlled measurement. — [Singh et al. 2017](https://people.eecs.berkeley.edu/~pabbeel/papers/2017-LaS-gradescope.pdf)

**Current AI-assisted grading / answer groups (2024–2026):**
- Answer Groups and AI-assisted grading "are only available on fixed-template PDF assignments". They are not available on Online Assignments, and they need an Institutional licence. — [Gradescope Guides: AI-assisted grading and answer groups](https://guides.gradescope.com/hc/en-us/articles/24838908062093-AI-assisted-grading-and-answer-groups) (snippet)
- Four question types are supported: Manually Grouped, Multiple Choice, Math Fill-in-the-blank, and Text Fill-in-the-blank. For the last three, "Gradescope AI will search through your students' submissions and group them by content". — [Gradescope Guides](https://guides.gradescope.com/hc/en-us/articles/24838908062093-AI-assisted-grading-and-answer-groups) (snippet)
- Alignment and extraction: "Gradescope AI compares each student submission to the original assignment template PDF by overlaying the two files and extracts the differences, displaying them in blue. Ideally, the only difference between the submission and the template should be the student's handwritten answer." — [Gradescope Guides](https://guides.gradescope.com/hc/en-us/articles/24838908062093-AI-assisted-grading-and-answer-groups) (snippet)
- Reading: the AI "is able to read student handwriting of English-language text and of math notation (including fractions, integral signs, etc.)". — [Gradescope Formatting Guide for AI-Assisted Grading](https://guides.gradescope.com/hc/en-us/articles/22238602932621-Formatting-Guide-for-AI-Assisted-Grading) (snippet)
- The main constraint: "the student answer [must be] on just one line, which is most easily enforced by providing a clear box or underscored area in the assignment template." Editing a question region in the outline deletes unconfirmed groups, and the question is then re-processed. — [Gradescope Formatting Guide](https://guides.gradescope.com/hc/en-us/articles/22238602932621-Formatting-Guide-for-AI-Assisted-Grading) (snippet)
- Workflow: the instructor reviews the suggested groups and can confirm, merge or adjust them. The remaining answers go to an "Ungrouped Answers" page for individual grading. Manually Grouped questions go straight to that page. The instructor grades one representative per group, and the grade applies to the whole group. — [Gradescope Guides](https://guides.gradescope.com/hc/en-us/articles/24838908062093-AI-assisted-grading-and-answer-groups) (snippet); [Chapman University 2024 blog](https://blogs.chapman.edu/academics/2024/05/28/streamline-your-grading-with-a-little-help-from-ai/)
- Gradescope is still used as the human "system of record" in 2025–26 research. In the UC Irvine study, for example, TA scores in Gradescope were the official grades and the AI was reference only. — [Yu et al., arXiv 2603.00895](https://arxiv.org/pdf/2603.00895)

### Inferences
- Gradescope's design has three parts: (a) fixed geometry drawn once per template, (b) overlay against the blank template to isolate the student's ink, and (c) reading only short one-line answers to cluster them, with a human grading each cluster once. This is the closest production analogue to the Pune problem. Its two key choices address exactly the Pune engine's weak spots. It does not infer which printed question an answer belongs to; the instructor-drawn box decides that. For non-numeric answers (even/odd, <, ticks) it does not need perfect reading, only consistent grouping plus one human confirmation per group.
- The overlay step (subtract the blank template, keep the difference) is a cheap way to separate child ink from printed boxes and text. Printed answer boxes are one of Pune's named failure sources.
- Gradescope cannot handle answers that aren't on a single line, and multi-line working falls outside AI grouping. This mirrors Pune's "working written beside answers" failure. Gradescope's answer is to force answer-box discipline in the template, not to add smarter reading.

### Gaps
- No published accuracy for Gradescope's handwriting reading or grouping (share of answers auto-grouped, grouping error rate). None was found in official docs or papers.
- No published figure for time saved by AI answer groups (as opposed to the 2017 dynamic-rubric survey data).
- Whether suggested groups carry confidence scores, and how Gradescope handles phone photos versus flatbed scans for the overlay, could not be confirmed. The official guides returned 403.

---

## Q2. Crowdmark: page matching, QR codes, how handwritten work is marked, AI features

### Takeaway
Crowdmark relies on known geometry through printed QR codes. Every page carries a QR code, so page identity and order are never inferred. AI is used only for administrative reading: OCR of handwritten names/IDs in one-character-per-box fields, and AI-assisted multiple-choice bubbles. The company states as policy that marking of handwritten work stays with humans.

### Cited Findings
- "Crowdmark places QR codes on each page of the assessment." QR-coded booklets can be pre-printed with student details and are then "pre-matched" to those students. — [Crowdmark: Matching booklets / pre-matched booklets](https://crowdmark.com/help/using-pre-matched-booklets/) (snippet); [Crowdmark: Creating a QR coded Administered assessment](https://www.crowdmark.com/help/creating-an-administered-assessment/) (snippet)
- Automated matching uses OCR on the cover page. Students write their information "one character per box" and must print clearly within the boxes, in uppercase, lowercase or both. — [Crowdmark: Using AI-assisted matching](https://www.crowdmark.com/help/using-automated-matching/) (snippet)
- Template geometry requirements: a blank band between 9 cm and 18 cm down the cover page for the matching region, plus 3.8 cm (1.5 in) for the QR code. — [Crowdmark: Using AI-assisted matching](https://www.crowdmark.com/help/using-automated-matching/) (snippet)
- Crowdmark has used AI "since 2016". Its policy is "to free educators from tedious administrative tasks". It "does not seek to replace educators by grading with AI", and it views teaching as "a fundamentally human-to-human experience". Its code uses AI "to match handwriting to known letters" in order to identify whose work it is. — [Crowdmark blog: How does Crowdmark use AI?](https://www.crowdmark.com/blog/how-does-crowdmark-use-artificial-intelligence/) (snippet)
- Crowdmark offers AI-assisted multiple-choice questions inside its booklets. — [Crowdmark help: Using AI-assisted multiple choice questions](https://www.crowdmark.com/help/using-multiple-choice-questions/) (title/snippet only)
- A 2024 University of Zurich tool catalogue lists Crowdmark's features as digitisation, collaborative grading, reusable comments, annotation and statistics. It lists no AI answer grading. — [UZH AI-assisted grading tool explorer: Crowdmark](https://www.df.uzh.ch/static/ai-assisted-grading/tools/crowdmark) (updated 23-Dec-2024)

### Inferences
- QR per page removes a whole class of errors that CBSE's 2026 rollout hit: mismatched and missing pages (see Q4). A small school printing its own worksheets can add a QR with worksheet ID + page to every page at almost no cost. The engine then knows exactly which template geometry applies before reading anything.
- The one-character-per-box cover-page design is a proven way to make handwriting machine-readable. It is directly usable for answer slots meant to hold a single digit or a short number.

### Gaps
- No published accuracy or time-saving figures for Crowdmark's name-matching OCR or MCQ reading were found.
- Found no 2025–26 announcement of LLM-based answer grading in Crowdmark. Whether one exists could not be confirmed, because the help/blog pages returned 403.

---

## Q3. Mathpix: handwritten math OCR claims, use in grading, API

### Takeaway
Mathpix is a strong commercial reader of handwritten math. It returns confidence scores and supports English, Hindi and Latin-script handwriting. Independent 2025–26 grading studies found it was overtaken by prompted LLM vision models on real student calculus work: 55% vs 84% "acceptable" transcriptions on a hard subset. It also cannot reconstruct diagrams. Its public accuracy claims are vendor-only.

### Cited Findings
- Vendor claims: it recognises "handwritten math (including advanced math)", "handwritten Hindi & all Latin alphabet languages", handwritten chemical diagrams and mixed text/math. It says users "choose Mathpix over AWS Textract, Google Vision API, and Azure Computer Vision" for handwriting. Its example response shows a confidence of 0.998. The page gives no accuracy percentage. — [Mathpix Handwriting Recognition](https://mathpix.com/handwriting-recognition)
- The OCR API reads printed and handwritten math, text, tables and chemical diagrams, covering "32 printed languages" and handwriting in English, Hindi and Latin-alphabet languages. — [Mathpix Convert/OCR API](https://mathpix.com/convert) (snippet)
- Independent, UC Irvine (2024–25): the team first "selected Mathpix as the most reliable choice at the time" (Fall 2024/Winter 2025). After GPT-4.1-mini was released, they re-ran the comparison. On a challenging subset of 171 handwritten solutions, GPT-4.1-mini with OCR-specific prompting reached 84% acceptable transcriptions against 55% for Mathpix. Across thousands of submissions, about 88% of GPT-4.1-mini transcriptions were acceptable. "Mathpix did not reconstruct any diagrams from student work." — [Yu et al., arXiv 2603.00895 (Mar 2026)](https://arxiv.org/pdf/2603.00895)
- Why the LLM won: "Unlike Mathpix, which primarily targets literal transcription, GPT-4.1-mini can leverage" problem context. Stating the problem in the prompt improved OCR. — [Yu et al. 2026](https://arxiv.org/pdf/2603.00895)
- Grading pipeline using Mathpix (Liu et al. 2024): scanned paper exams were transcribed with GPT-4V + Mathpix and checked with GPT-4 against rubric rules, reaching "grading accuracy of ∼60%". Reading (recognition + layout) was identified as the primary challenge. — cited in [Levine et al., arXiv 2605.19043 (May 2026)](https://arxiv.org/pdf/2605.19043); also referenced in [Pensieve Grader paper](https://arxiv.org/pdf/2507.01431)

### Inferences
- For a Grade 2–4 worksheet, the recognition target (digits, <, >, =, short words) is far simpler than calculus LaTeX. Mathpix's advantage on advanced notation matters little here. Supplying context (which question, which answer set is allowed) mattered more than the choice of OCR engine in the UC Irvine data. This suggests the Pune engine's reading errors may shrink more from per-slot context than from swapping Textract for Mathpix.

### Gaps
- No independent digit-level accuracy benchmark for Mathpix on children's handwriting was found.
- No named grading product was confirmed to use Mathpix in production (Mathpix says only "biggest Edtech companies").

---

## Q4. Exam-board on-screen marking (Pearson ePEN, RM Assessor, Cambridge, CBSE): scanning, item clips, routing, auto-marking, quality control

### Takeaway
High-stakes boards scan paper scripts and cut them into per-item "clips" using the known geometry of the printed answer booklet. Each clip goes to a human marker who marks one item at a time. Quality is controlled by seeded items with pre-agreed "true" scores. Machines auto-mark only objective items such as multiple choice. None of the boards researched auto-reads handwritten constructed answers for live marks. CBSE's first full on-screen rollout (2026) failed mainly on scanning and page-identity problems, not on marking logic.

### Cited Findings
**Pearson ePEN (Edexcel):**
- ePEN "displays questions from scanned scripts for examiners to access and mark from home". Scripts are "scanned into the system and divided into individual responses which correspond to each item". — [Pearson ePEN](https://qualifications.pearson.com/en/support/support-for-you/assessment-associates/aa-gateway/online-marking/epen2.html) (snippet); [Pearson Glossary of Online Marking Terms v7](https://www1.edexcel.org.uk/ePEN-training/content/Glossary%20of%20Online%20Marking%20Terms%20Version%207.pdf)
- "Out of Clip": when a response lies outside the item's clip, or is unreadable, the marker sends it to Review. A senior examiner then sees "the image of the whole script" ("Pulled Paper"). If it is still unmarkable, a hard copy is printed and sent. — [Pearson Glossary v7](https://www1.edexcel.org.uk/ePEN-training/content/Glossary%20of%20Online%20Marking%20Terms%20Version%207.pdf)
- "Rubric items" handle routing when a candidate does not show which question they answered "using the Cross Boxes". They are "only necessary where more than one question shares an answer space". — [Pearson Glossary v7](https://www1.edexcel.org.uk/ePEN-training/content/Glossary%20of%20Online%20Marking%20Terms%20Version%207.pdf)
- Multi-part items are split into "traits". For example, item 6663_01_Q01a-c has three traits (Q01a, Q01b, Q01c), each shown as a row in the marking grid. — [Pearson Glossary v7](https://www1.edexcel.org.uk/ePEN-training/content/Glossary%20of%20Online%20Marking%20Terms%20Version%207.pdf)
- "Exception scripts (Whitemail)": scripts that cannot be scanned, e.g. written in coloured pen, or on A3 or coloured paper, "must be marked traditionally". — [Pearson Glossary v7](https://www1.edexcel.org.uk/ePEN-training/content/Glossary%20of%20Online%20Marking%20Terms%20Version%207.pdf)
- Quality control: markers must pass a Qualification Set before live marking. "Validity items" with a true score appear "every 1 in 25 items marked (4% of a Marker's allocation)". Senior staff also "backread" samples and can "cap" (stop) a marker. — [Pearson Glossary v7](https://www1.edexcel.org.uk/ePEN-training/content/Glossary%20of%20Online%20Marking%20Terms%20Version%207.pdf)

**RM Assessor (used by many UK/international boards):**
- Seeding means "randomly introducing scripts or items that have already been marked and given an agreed score". Seeds look identical to live scripts. The system compares the examiner's mark with the agreed mark, gives ongoing feedback, and can temporarily suspend examiners. — [RM Assessor brochure](https://silo.tips/download/rm-assessor-discover-the-most-widely-used-innovative-e-marking-platform-in-the-w) (snippet); [RM: Test collation and marking](https://www.rm.com/assessment/collect-collate-and-mark) (snippet)
- "Objective item types (e.g. multiple choice) can be marked automatically by a machine." Constructed responses are marked by humans, and tolerances and automated rules trigger intervention. — [RM: Test collation and marking](https://www.rm.com/assessment/collect-collate-and-mark) (snippet)
- RM's AI marking (2025–26) is aimed at digital exams. It is being tested in three modes: AI + human double marking, AI double marking only at grade boundaries, and AI alone. — [RM: AI in Assessment](https://www.rm.com/assessment/services/ai-in-assessment) (snippet)

**Cambridge (UCLES), older, flagged by date:**
- 2002: paper scripts were scanned at UCLES or regional bureaus, and images were "distributed electronically and marked on screen". "Question-level marks … are captured … without manual intervention." Scripts were apportioned dynamically to examiners as each became ready. A November 2000 trial covered O Level Mathematics and other subjects, and concluded that marking whole scanned scripts "would be likely to be as reliable as conventional" marking. — [UCLES, On Screen Marking of Scanned Paper Scripts, 7-Jan-2002](https://www.cambridgeassessment.org.uk/Images/109688-on-screen-marking-of-scanned-paper-scripts.pdf)
- UCLES–Oxford auto-marking research (pre-LLM, 2000s): handwritten short answers were typed in by humans before pattern-based scoring. The scoring reached 81% agreement with examiners, rising to 90% when alternative wordings were added to the patterns. — [UCLES, Auto-marking 2](https://www.cambridgeassessment.org.uk/Images/461008-auto-marking-2-an-update-on-the-ucles-oxford-university-research-into-using-computational-linguistics-to-score-short-free-text-responses..pdf) (snippet)

**CBSE On-Screen Marking (India, 2026):**
- On 9-Feb-2026 CBSE mandated OSM for Class 12. Students still write in physical answer books, which are scanned (at CBSE Regional Offices, per reports) and uploaded. Examiners evaluate "question-wise", with automatic totalling and structured moderation. — [Wikipedia: 2026 CBSE OSM controversy](https://en.wikipedia.org/wiki/2026_CBSE_On-Screen_Marking_controversy); [CBSE FAQ on OSM, 18-May-2026](https://www.cbse.gov.in/cbsenew/documents/FAQ-OSM_18052026.pdf) (snippet); [Careers360](https://news.careers360.com/cbse-2026-class-12-on-screen-marking-system-portal-onmark-co-in-teacher-student-reaction-osm-bias-risk-glitch-paper-scan-errors) (snippet)
- Scale: 98,66,622 answer books, about 40 crore scanned pages, and about 70,000 evaluators. The evaluation window was compressed from 12 to 9 days. The rollout went straight to full scale without phased piloting. The vendor was Coempt Eduteck (OnMark platform). — [The Probe](https://theprobe.in/education/cbse-osm-result-2026-examination-failure-india-11891206); [Wikipedia](https://en.wikipedia.org/wiki/2026_CBSE_On-Screen_Marking_controversy)
- Failures reported after results on 13-May-2026: blurred or illegible scans, missing pages, and students receiving another student's answer sheets. CBSE acknowledged discarding "around 30 answer sheets due to issues like unclear images". There were 4,04,319 applications for scanned copies. Fees were cut (photocopy ₹700→₹100, verification ₹500→₹100, re-evaluation ₹100→₹25 per question). The pass rate fell from 88.39% to 85.2%. The Chairman and Secretary were removed. — [Wikipedia](https://en.wikipedia.org/wiki/2026_CBSE_On-Screen_Marking_controversy); [The Probe](https://theprobe.in/education/cbse-osm-result-2026-examination-failure-india-11891206)
- No AI reading or auto-marking of handwriting in CBSE OSM was reported. — [Wikipedia](https://en.wikipedia.org/wiki/2026_CBSE_On-Screen_Marking_controversy); [The Probe](https://theprobe.in/education/cbse-osm-result-2026-examination-failure-india-11891206)

### Inferences
- The boards' approach has three parts: fixed booklet geometry leading to per-item clips, an explicit "Out of Clip" escape path to the whole page, and seeded true-score items for quality control. This maps directly onto a small-school engine. (1) Clip each sub-part by template geometry. (2) When ink falls outside the clip, or a clip is empty while ink sits nearby, route to "whole page" teacher review instead of guessing the binding. (3) Seed a few teacher-confirmed answers into every batch to measure the engine's confidently-wrong rate continuously.
- Pearson's "rubric item / cross box" and "trait" ideas are the board-level fix for multi-part questions and shared answer spaces. Each sub-part gets its own addressable slot on paper, and the paper design removes ambiguity so the software does not have to.
- CBSE's failures (blur, missing pages, wrong student) are capture and identity failures. Per-page QR (Crowdmark), an image-quality gate, and page-count checks are the cheap defences.

### Gaps
- Could not access detailed RM Assessor or Cambridge/IB documentation on how clip zones are defined (e.g. template coordinates vs. anchor marks), or how blank-response detection works.
- No board was found publishing auto-marking of short handwritten numeric answers from paper scripts. Absence of evidence is not proof that no board does it.
- No quantified CBSE re-evaluation outcomes (how many marks changed) were found.

---

## Q5. Edtech graders for young children and classroom tools: do they read handwriting or avoid it?

### Takeaway
The established products avoid free handwriting on paper. Kumon moves the worksheet onto a tablet with a stylus, and marking there is done by instructors. GradeCam reads only handwritten digits in its designated numeric question type, as a paid add-on. A new wave of photo-based "AI worksheet graders" (2025–26), including some India-focused ones, claim 95–99%+ accuracy. Those claims are vendor marketing with no independent measurement found. The more credible ones say they flag unreadable answers for teacher review.

### Cited Findings
- Kumon Connect: students do the identical worksheets on a tablet, and levels 5A and above must use a stylus. Work is "submitted for daily grading", and students are notified when corrections are needed. Instructors can replay the work and annotate. The sources do not describe automatic handwriting reading. — [Kumon: How Kumon Connect works](https://www.kumon.com/resources/how-kumon-connect-works/); [Kumon Connect](https://www.kumon.com/kumon-connect)
- GradeCam's AI, "Aita", reads handwritten numeric characters. Students "bypass the bubble grid and simply write out their number answers". The feature is an add-on only for GradeCam Go! School/District licences. — [Cult of Pedagogy](https://www.cultofpedagogy.com/gradecam/) (snippet); [Engaging Technologies: new GradeCam question types](https://www.engaging-technologies.com/new-gradecam-question-types/) (snippet)
- GradingPal (US, K-5) claims "95%+ OCR accuracy" even on early elementary handwriting. It "flags anything it cannot read instead of guessing", and teachers approve suggested scores against "quoted evidence". Teachers can upload the blank PDF. The page gives no independent benchmark. — [GradingPal OCR blog](https://www.gradingpal.com/blog/how-gradingpal-s-ocr-technology-grades-handwritten-math-and-science-worksheets); [GradingPal elementary](https://www.gradingpal.com/ai-grading-elementary)
- GradeLab claims "99%+ accuracy in reading handwritten answers across all subjects" from scans or phone photos. — [GradeLab](https://gradelab.io/ai-handwritten-grading) (vendor claim, snippet)
- India-focused vendors: Eklavvya claims "95%+ accuracy", "results in 8 days instead of 45", "200+ faculty hours" saved, and support for English, Hindi, Marathi, Tamil and Telugu. ClassMap claims 95%+ multilingual OCR. E-Valuate AI and Chanakya AI market similar handwritten answer-sheet checking. — [Eklavvya schools](https://www.eklavvya.com/ai-answersheet-evaluation-school/); [Eklavvya blog](https://www.eklavvya.com/blog/ai-answer-sheet-checking/); [ClassMap](https://classmap.in/); [E-Valuate AI](https://evaluate-ai.app/); [Chanakya AI](https://aichanakya.in/) (all vendor claims, snippets)

### Inferences
- "95%+" OCR claims are usually per-character or per-response reading rates on unstated data. They are not comparable to the Pune engine's "82% exact, ~1% confidently wrong, 26% to teacher", which is a per-answer-slot end-to-end measure that includes binding. Treat all vendor numbers as unverified until tested on the school's own sheets.
- The mature pattern for young children is to constrain the input rather than read free handwriting better. Options are a tablet (Kumon), a digit-only field (GradeCam), or bubbles.

### Gaps
- Not researched within budget: Photomath/Brainly (solvers, not graders), Snapask, Squirrel AI (tablet-based adaptive), Byju's/Toppr/Cuemath paper-checking workflows, ZipGrade and Akindi (believed to be bubble-sheet OMR only, not verified here). No sources were collected for these.
- GradeCam's handling of uncertain digit reads (teacher confirmation or not) and its accuracy could not be verified; its partner pages returned 403.

---

## Q6. Research systems (2019–2026) for automatically grading handwritten math on real student work

### Takeaway
The 2025–26 systems that work on real student work all use fixed answer boxes, crop per region, and read with a vision LLM given the question's context. They report 89–99% rubric-item accuracy, or more than 90% of scores within ±1 point, on university math. Most errors come from reading, not judging: 87% of errors in the best UIUC model. Blank boxes cause hallucinated answers unless a presence check exists. Reaching human-level reliability still requires routing somewhere between 17% and 70% of items to humans. One study found no confidence threshold stable enough to skip human review.

### Cited Findings
**UC Irvine calculus, the largest real-course study (Yu et al., arXiv 2603.00895, Mar 2026):**
- Deployment: 3 terms, 20 quizzes, more than 1,000 students. Low stakes (quizzes ≈10% of the grade); AI scores were reference only. — [Yu et al. 2026](https://arxiv.org/pdf/2603.00895)
- Pipeline: "a standardized answer-sheet format that separates each problem into a solution region and a final-answer region". OCR and grading run "at the region level (rather than on whole-page inputs) to reduce cross-problem interference and hallucination". — [Yu et al. 2026](https://arxiv.org/pdf/2603.00895)
- Blank boxes caused the model to "generate full solutions". The fix was to pre-print the words "Solution" and "Final Answer" inside the boxes, plus a prompt instruction (Answer Sheet Version 2). An instruction not to correct the student's work reduced autocorrection to under 2%. — [Yu et al. 2026](https://arxiv.org/pdf/2603.00895)
- The final-answer box "provides little surrounding context and is therefore more prone to OCR errors". A correct final answer can be misread even when the working is transcribed correctly. — [Yu et al. 2026](https://arxiv.org/pdf/2603.00895)
- Unsolved: crossed-out or scribbled text (OCR "may transcribe erased work or drop nearby valid symbols"), and nested fractions. Submissions were excluded for "segmentation failures when students wrote outside designated boxes", and one TA section was excluded for scanning artifacts. — [Yu et al. 2026](https://arxiv.org/pdf/2603.00895)
- Results against TAs on 3,945 responses: AI averaged 0.40 points lower (SD 1.12). Quiz-level mean absolute gap was 0.5–1.06 points, and 68–86% of scores were within 1 point. Independent review of 3,851 responses: more than 90% within ±1; 79.79% fully correct, 9.55% acceptable, 10.67% incorrect. OCR input was rated acceptable for 87.64%. — [Yu et al. 2026](https://arxiv.org/pdf/2603.00895)

**UIUC / PrairieLearn (Levine et al., arXiv 2605.19043, May 2026):**
- Students photograph their own work, can preview and crop it, and can resubmit if it is unclear. One multimodal LLM call does both transcription and rubric grading. The courses had n=245 in Course 2 plus Course 1. — [Levine et al. 2026](https://arxiv.org/pdf/2605.19043)
- Gemini 3 Flash had the best rubric-item accuracy: "89% on Course 2 to over 99% on Course 1" (≈95% overall). "Most errors (87%) stemmed from inaccurate transcription". Its errors skewed 2.5:1 toward false positives, "occasionally hallucinating correct answers when struggling to interpret handwriting". — [Levine et al. 2026](https://arxiv.org/pdf/2605.19043)
- Failure modes: blurry images, rotated text, hallucinated text resembling the reference solution, and equivalent forms marked wrong (rounded decimals vs exact fractions). Model disagreement showed no consistent lenient/strict pattern usable for routing. — [Levine et al. 2026](https://arxiv.org/pdf/2605.19043)

**VUB Brussels, human-in-the-loop (arXiv 2603.13083, 2026):**
- A standardised answer sheet had two delineated answer boxes and a bubble-coded student-number area. Template recognition identified fixed structural elements. Boxes were "automatically cropped into separate images" and anonymised. GPT-5.1 graded each response 5 times, and every score was reviewed by an instructor. — [arXiv 2603.13083](https://arxiv.org/html/2603.13083)
- Quadratically weighted κ: human–human 0.70–0.96; human–LLM 0.50–0.91. About 3% of human–GPT comparisons were larger outliers. Time saved was 23.3% on average (95% CI 1.1–40.5%). On routing, "no stable threshold emerged" that separated benign variation from errors, so human verification stayed mandatory. Student-number bubbles failed OCR when lightly filled. — [arXiv 2603.13083](https://arxiv.org/html/2603.13083)

**Kortemeyer et al., calculus exam (arXiv 2510.05162, 2025) and physics (PRPER 2025):**
- 349 scanned exams. The TAs' grading marks were removed with OpenCV colour filtering, since students were not allowed to write in red, pink or green. GPT-5 received the student-work image plus the rubric page. — [arXiv 2510.05162](https://arxiv.org/html/2510.05162v2)
- Unfiltered, the AI reached R² ≈ 0.85 against TAs ("adequate for low-stakes feedback"). The human-in-the-loop filter combined a partial-credit threshold with an IRT (2PL) "risk" score. At the loose setting, 81% of items were auto-accepted at R² ≈ 0.89. At the strict setting, about 30% were auto-accepted (≈70% went to humans) at R² ≈ 0.95. — [arXiv 2510.05162](https://arxiv.org/html/2510.05162v2); corroborated in [Levine et al. 2026](https://arxiv.org/pdf/2605.19043) and [Kortemeyer et al., PRPER 21, 010136](https://journals.aps.org/prper/abstract/10.1103/PhysRevPhysEducRes.21.010136)
- Failures: work "outside designated answer boxes or on loose sheets was missed", follow-through credit, and graphs. Recommendations: "clearly designated answer regions with labels mirroring rubric keys; include page anchors", pencil and erasing rather than crossing out, and no background grids. — [arXiv 2510.05162](https://arxiv.org/html/2510.05162v2)

**Ljubljana, engineering quizzes (Perš et al., arXiv 2601.00730, Jan 2026):**
- The exam uses unconstrained A4 paper. The lecturer's handwritten reference solution is converted to a text summary. An "answer presence guardrail" checks which tasks contain an answer before any scoring. It was added after the model hallucinated content for blank regions, which the authors call "operationally unacceptable". — [Perš et al. 2026](https://arxiv.org/pdf/2601.00730)
- Three independent grader calls feed a supervisor, with rigid templates and deterministic validation. If output parsing fails, a human is required. Results: about 8-point mean absolute difference from lecturer grades, and a manual-review trigger rate of about 17% at a disagreement threshold of Dmax = 40. — [Perš et al. 2026](https://arxiv.org/pdf/2601.00730)

**Pensieve Grader, commercial and vendor-authored (arXiv 2507.01431, Jul 2025):**
- Deployed at more than 20 institutions on more than 300,000 responses. Bulk scans are auto-matched to students "by recognizing handwritten names". Instructors set each question's format (single/multi-select MC, drawing, text/code). Transcriptions carry high/low confidence, and grades carry high/medium/low confidence. — [Pensieve Grader](https://arxiv.org/pdf/2507.01431)
- Accuracy of high-confidence AI grades: 95.4% overall (Math 93.5%, Physics 94.5%, CS 95.8%, Chem 97.5%). The claimed time saving is 40–80% (65% average). That figure is modelled, not measured: it assumes humans review all low-confidence grades plus about 5% of high-confidence ones. — [Pensieve Grader](https://arxiv.org/pdf/2507.01431)

**Other, not fully read:**
- Caraeni, Scarlatos & Lan (2024) evaluated GPT-4o on grading real handwritten college math exam responses. — [arXiv 2411.05231](https://arxiv.org/abs/2411.05231) (abstract/snippet only)
- VEHME (2025), an open vision-language model for handwritten math expressions, is reported to match or beat GPT-4o and Gemini 2.0 Flash on messy handwriting. This is press-release level. — [TechXplore](https://techxplore.com/news/2025-12-ai-accurately-grades-messy-handwritten.html); [arXiv 2510.22798](https://arxiv.org/pdf/2510.22798)

### Inferences
- Every credible 2025–26 system solved the binding problem before reading. They did it with pre-printed boxes, per-region crops and sometimes QR or bubble IDs, and the one that ran on whole pages (Kortemeyer) listed out-of-box work as a top failure. Direct lesson for Pune: move from "Textract whole page + geometry rules to find questions" to "known template, crop each sub-part slot, read the crop with its question context".
- Blank-slot hallucination is a known hazard with LLM readers, and three independent teams hit it (UCI, Ljubljana, UIUC). If Pune adds an LLM/VLM reader, an explicit ink-present/absent check per slot is mandatory.
- Measured automation vs. accuracy trade-off: at human-level agreement, 17–70% of items still go to humans (Ljubljana ≈17% at a loose threshold; Kortemeyer 19% at R² 0.89, 70% at R² 0.95). VUB kept 100% human review and still saved 23%. Pune's 26%-to-teacher rate is within the range these systems accept, but its 82% exact reading is below the ~88–95% reported on university work with fixed boxes. That gap is consistent with binding errors, which those systems design out.
- Teacher red marks can be removed by colour (Kortemeyer's OpenCV step) because the red ink is a different colour from the child's pencil. This carries over directly to Pune's red ticks/crosses.

### Gaps
- No 2019–2026 study was found on automatically grading primary-school (Grade 2–4) handwritten math worksheets on real student work. All rigorous studies are university level.
- No study reported per-slot binding accuracy separately. Binding failures show up only as exclusions or "outside the box" failure notes.

---

## Q7. Across all systems: known geometry vs layout inference, reading vs routing, realistic automation and accuracy

### Takeaway
In production, known template geometry is close to universal. Gradescope uses drawn boxes plus template overlay, Crowdmark uses a QR code on each page, exam boards cut per-item clips from fixed booklets, and research systems use standardised answer sheets. Layout inference appears only in unverified vendor photo apps and whole-page LLM prototypes. Automatic reading is used where the answer format is constrained: names in boxes, digits, one-line fill-ins, bubbles. Reading is used to group answers or to suggest a grade, and humans confirm. Measured end-to-end, the full-auto share at human-level quality is roughly 30–83%, and the rest is routed.

### Cited Findings
- Gradescope: geometry is instructor-drawn on the blank template, the overlay extracts the difference, and only one-line answers are AI-grouped, with a human confirming. — [Singh et al. 2017](https://people.eecs.berkeley.edu/~pabbeel/papers/2017-LaS-gradescope.pdf); [Gradescope Guides](https://guides.gradescope.com/hc/en-us/articles/24838908062093-AI-assisted-grading-and-answer-groups) (snippet)
- Crowdmark: a QR code on every page gives geometry and identity. AI reads only names/IDs and MCQs, and humans mark the answers. — [Crowdmark AI blog](https://www.crowdmark.com/blog/how-does-crowdmark-use-artificial-intelligence/) (snippet); [Crowdmark matching](https://www.crowdmark.com/help/using-automated-matching/) (snippet)
- Exam boards: scripts are divided into item responses (clips), with an "Out of Clip" escape to the whole script. Humans mark all constructed responses, machines mark only objective items, and seeds run at 1 in 25. — [Pearson Glossary v7](https://www1.edexcel.org.uk/ePEN-training/content/Glossary%20of%20Online%20Marking%20Terms%20Version%207.pdf); [RM](https://www.rm.com/assessment/collect-collate-and-mark) (snippet)
- Research systems: standardised boxes with region-level OCR (UCI, VUB), designated regions plus page anchors recommended (Kortemeyer), and whole-page processing with ensemble and presence check (Ljubljana). — [Yu et al.](https://arxiv.org/pdf/2603.00895); [VUB](https://arxiv.org/html/2603.13083); [Kortemeyer](https://arxiv.org/html/2510.05162v2); [Perš et al.](https://arxiv.org/pdf/2601.00730)
- Automation/accuracy benchmarks (all university level):
  - Kortemeyer: 81% auto-accepted at R² 0.89, or 30% at R² 0.95.
  - Ljubljana: ≈17% review trigger.
  - Pensieve: 95.4% accuracy on high-confidence grades (vendor).
  - UIUC: 89–99% rubric-item accuracy.
  - UCI: >90% within ±1 point.
  - VUB: 23.3% time saved with 100% human review.
  - Liu et al. 2024 (Mathpix + GPT-4): ~60%.
  - — [Kortemeyer](https://arxiv.org/html/2510.05162v2); [Perš](https://arxiv.org/pdf/2601.00730); [Pensieve](https://arxiv.org/pdf/2507.01431); [Levine](https://arxiv.org/pdf/2605.19043); [Yu](https://arxiv.org/pdf/2603.00895); [VUB](https://arxiv.org/html/2603.13083)
- CBSE 2026 shows the main risk at scale is capture and identity: blur, missing pages, wrong student. — [Wikipedia](https://en.wikipedia.org/wiki/2026_CBSE_On-Screen_Marking_controversy)

### Inferences (what a small school's engine could copy, ranked by evidence strength)
1. **Known geometry per worksheet template, not layout inference** (unanimous across production and research). Mark answer-slot boxes once per worksheet, one per sub-part, the way Gradescope's outline does. Register each photo to the template using corner anchors or a per-page QR (Crowdmark / Kortemeyer's "page anchors"). Then crop each slot. This targets Pune's biggest failure, binding answers to question and sub-part.
2. **Template subtraction plus colour filtering** to isolate the child's pencil. Gradescope overlays the template and keeps the blue difference; Kortemeyer removes red marks with OpenCV. This removes printed boxes and teacher ticks before reading.
3. **Out-of-clip route** (Pearson). If ink is outside every slot, or a slot is empty with ink nearby, send the whole page to the teacher. Do not guess.
4. **Presence check before reading** (UCI, Ljubljana, UIUC). Never let a reader "see" an answer in a blank slot.
5. **Read each crop with its question context and an allowed-answer vocabulary** (UCI: context beat Mathpix). Examples: digits only; one of {<, >, =}; one of {even, odd}; tick/no-tick.
6. **Group-then-confirm for non-numeric and low-confidence slots** (Gradescope answer groups). Cluster identical-looking crops per slot and let the teacher approve each cluster once. This cuts review time without claiming automatic reading.
7. **Seeded QC** (Pearson 1-in-25 validity items, RM seeding). Keep a stream of teacher-confirmed slots to measure the confidently-wrong rate continuously.
8. **Paper design fixes what software can't.** One slot per sub-part, labels pre-printed in boxes (UCI V2 sheet), working space separated from the answer box (UCI), pencil and erasing rather than crossing out, no background grids (Kortemeyer).

### Gaps
- No published system handles Grade 2–4 paper worksheets from phone photos with measured, independent accuracy. The closest evidence comes from university settings with better handwriting and flatbed or document-camera capture.
- No production vendor publishes the share of answers auto-read versus human-routed for handwritten short answers (Gradescope, Crowdmark, GradeCam).
