# Designing worksheets and answer sheets that machines can read: form design, page alignment, and how much accuracy the design adds

Scope: how to design paper so handwriting can be read by machine (answer boxes, comb fields, registration marks, per-page codes, dropout colours, OMR bubbles, layout); how a photo or scan is matched to a known page layout; and the measured accuracy of designed forms compared with free-layout pages. Sources run from 2001 to 2026, each dated. Vendor claims are marked as such. [snippet] means the page returned HTTP 403 and only the search-result text was used. Links are reference-style; their URLs are listed at the end of the file.

## Q1. Form-design guidelines from ICR / forms-processing practice

### Takeaway
Forms-processing practice has settled on one character per separate box. The boxes are printed in a colour that disappears on scan or can be removed in software. Each page carries four or five solid black registration marks, a machine-readable page ID, and clear space between answer fields and printed text. "Text over a line", which is how legacy worksheets usually ask for answers, is the layout the ABBYY guide says not to use when high accuracy is needed. The same guide says pencil gives the worst recognition.

### Cited Findings
**Field styles (all from the [ABBYY guide, 2009, FlexiCapture 8][abbyy])**
- ABBYY lists six text-marking types: text over a line, letters in conjoined frames, letters in separate frames, letters on a comb, text in a frame, and text in a frame with a comb.
- Printed character cells make writers "less likely to join the letters together". A comb, or a frame with a comb, is harder to read because only the width is fixed. On a comb with no frame, "letters can be written either too small or too large".
- Text over a line fixes neither height nor width: "not recommended for forms requiring a high degree of recognition accuracy".
- Writing over a box border matters little on dropout or raster forms, where the borders vanish. On black-line forms it "may result in a significant decrease in recognition quality".
- ABBYY recommends printing a sample of correct completion on the form. The UN census guide likewise recommends a writing example on every form plus training for the people filling it in ([UN Statistics Division 2009][un]).

**Dimensions (ABBYY, sized for adults) ([ABBYY 2009][abbyy])**
- Character cells: 4×5 mm recommended. Smaller cells need precision that is "very difficult to achieve". Larger cells encourage "abnormally large letters", so the cell should match average letter size. At least 1–1.2 mm between cells, at least 2.5–3 mm between field lines, and 1 pt border lines.
- Combs: notches 5 mm apart and 0.9–1.2 mm tall. Stacked combs at least 7.5–8 mm apart.
- Checkboxes: 3.5×3.5, 4×4, 4.5×4.5 or 5×5 mm, with 0.4 mm borders (circles must fit inside those squares). The label must sit at least 2/3 of the box size away.
- Spacing: at least 2 mm between neighbouring elements. Black explanatory text needs 1.5–2 mm clearance and must not overlap fields. Page margins at least 8 mm, 12 mm recommended.

**Registration marks and page ID ([ABBYY 2009][abbyy])**
- Five standard reference marks are recommended: one in each corner, forming a rectangle, plus one more on one side (the asymmetry gives orientation). Black squares must all be the same size, 4×4 to 8×8 mm, with 5×5 mm recommended; rectangles are not allowed. Crosses and corners use 0.3–1 mm lines. Each mark must be at least 3 mm from other elements and at least 8 mm from the page edge, printed in black.
- Form identifiers: barcodes are recommended. When a barcode also serves as a reference mark: EAN-13, at least 47–50 mm wide, at least 12–15 mm tall, at least 10 mm clearance.
- Print tolerance: element positions may shift by no more than 0.15%, about 0.5 mm on A4. Printer output must be at least 600 dpi, all copies from one source file, ideally on the same printer model. Photocopying is advised against: it "can slightly change dimensions" and thickens lines.
- A unique barcode or number on every form lets software catch a form scanned twice ([UN 2009][un]). In the 2000 US Census, "every Census form has a unique bar code identification" ([Lockheed Martin press release, 8 Jan 2001, vendor][lm]).
- OMR scanners need "timing marks" or "skunk marks" printed down the form edge ([UN 2009][un]).

**Dropout colour ([ABBYY 2009][abbyy]; [ABBYY FC12 help][abbyy12])**
- A dropout form prints the boxes, and optionally the instructions, in a light colour that disappears on scan, leaving only the reference marks and the writing. ABBYY rates this "very high recognition quality", the least sensitive to writing over borders and the fastest. The costs are colour-filtered scanning and lower legibility for the writer.
- The background is usually light red-orange or green. Red-orange is preferred for maximum contrast with blue ink. Blue is ruled out for handwritten forms because a blue background "may merge with the blue ink". Instructions printed in the dropout colour (at higher saturation) can sit anywhere, even inside fields.
- The black-and-white alternatives are dotted ("raster") borders, 0.39 pt dots spaced 5× the dot size and removed by despeckling, and solid-line forms, which are "very sensitive to text overlapping field borders".
- Dropout needs consistent ink across the print run ([UN 2009][un]).

**Writing implement ([ABBYY 2009][abbyy])**
- Black ballpoint, gel or capillary pen is best; dark blue and violet are acceptable; felt-tips are too thick. "Recognition is worst in the case of forms completed by pencil or using a light ink."

**Paper and layout ([UN 2009][un])**
- Typical paper is 90 gsm. On two-sided forms, response areas should not sit directly behind each other, because show-through causes wrong readings. Avoid folds, which cause skew and stretch. Prefer single-page forms. Restricting a field's allowed characters (e.g., "1 to 5") improves recognition.

**Vendor counterpoint**
- Parascript (blog, 14 Feb 2018) argues that boxes and combs exist only because most engines cannot separate characters, and that its unconstrained-handprint engine "performs much better on forms that have not been redesigned". The post gives no numbers ([Parascript, vendor][para]).

### Inferences
- **Red pen and red dropout conflict.** ABBYY's preferred dropout colour is red-orange, but teachers mark in red. Removing red would also remove the teacher's marks. That helps when reading the child's answer and hurts when the engine needs the teacher's tick. Phones capture colour, so the engine can remove the box colour in software. Pencil is grey, the teacher's pen is red, and light-green boxes differ from both, so all three separate by hue. This colour choice is an inference to test on real photos.
- **Pencil is a known weak spot.** Keep greyscale or colour images, not black-and-white ones, because a fixed black/white threshold erases faint pencil first.
- **Legacy answers are the hardest layout.** Answers after "=", on underlines, or in open working space match ABBYY's least reliable "text over a line" style. New sheets should use separate one-digit boxes, set apart from the printed sum and from a separate working area.

### Gaps
- No 2018–2026 vendor document (ABBYY, Kofax, Parascript) was found with measured accuracy by field style. The ABBYY table of recommended dropout colours (Pantone numbers) did not extract from the PDF.

## Q2. How census bureaus and exam boards design paper for machine reading, and the automation and error rates they report

### Takeaway
Censuses that used purpose-built scannable forms report about 99.8–99.9% accuracy for tick marks and 98.9–99.7% for handwritten numbers. These are whole-pipeline figures: every low-confidence field was keyed by a person. They are not raw machine accuracy. Large school assessments (NAEP, TIMSS) scan booklets but use the machine only for bubbles and page images; people score the handwritten answers. No official Indian board or NTA error rates were found.

### Cited Findings
**England & Wales 2011 Census ([ONS 2011 General Report, Ch. 5][ons])**
- Pipeline: scan; automated image quality check (image size, expected barcodes present); "data lift and registration"; OMR for tick boxes, OCR for text and numeric boxes, and contextual checks. Fields "that could not be recognised automatically with sufficiently high accuracy" were keyed by hand. Accuracy was checked by re-keying a sample, with a second keyer settling mismatches.
- Achieved accuracy in 2011 against target (2001 in brackets):
  - Marks: target 99.30%, achieved 99.85% (99.84%)
  - Numeric: target 98.00%, achieved 98.93% (99.75%)
  - Alphanumeric: target 95.00%, achieved 97.58% (98.99%)
  - Year of birth: target 99.95%, achieved 100.00%
  - Sex: target 99.50%, achieved 99.96%
  - Marital status: target 99.50%, achieved 99.92%

**US Census 2000, DCS 2000 ([Lockheed Martin 2001, vendor][lm])**
- About 148 million forms. First pass: OMR 99.89% (against a 99% requirement) and handwriting OCR 99.4% (against 98%). Second pass: OMR 99.88%, OCR 99.7%. Manual keying above 97.6% (goal 96.5%).
- 0.8% of forms (about 1.2 million) were rescanned, and keying operators were cut "by as much as 75 percent". This was the Census Bureau's first automated reading of handwriting.

**Morocco 2004 Census, ICR ([UN 2009][un])**
- A2iA FieldReader engine, minimum 200 DPI. Confidence thresholds: 95% for fields with no later logic checks, 85% for fields with later checks; below-threshold fields were key-corrected. Raising all thresholds to 95% "considerably" increased keying.
- Pre-test on 400 districts (about 72,000 questionnaires): automatic reading error 3.56–3.57 per 10,000, against 19.95 per 10,000 for keying, five times worse. Acceptable quality level 0.52%.

**Indicative engine figures, per character, western-script handwriting ([UN 2009][un])**
- Numeric in isolated fields (one box per character): **98%**. Numeric in semi-constrained fields (one box for several characters): **95–96%**. Upper case only: 90%. Lower case only: 85–87%. Mixed case: 75–80%. Mixed letters and digits: "50% or less".
- OMR: up to 15,000 forms per hour at 99.5–99.99% accuracy (supplier figures; real throughput is lower).
- ICR only for unjoined writing. Even high-confidence characters usually go to "mass verification": all images read as the same character are shown together for a person to confirm. "ICR solutions cannot make bad forms good."
- Example engine output for one handwritten 8: "8 = 93.4%, 6 = 44.2%, 3 = 34.9%". Application rules decide whether to accept it or send it to keying.

**Educational assessments**
- NAEP: Pearson scans the booklets. Multiple-choice answers are scored electronically; handwritten answers are imaged and scored on screen by human scorers, over 3 million a year, with calibration sets against score drift ([NCES scoring][naep1]; [NCES processing][naep2]).
- TIMSS paper booklets: scored by people using scoring guides, with responses typed in through IEA's Data Management Expert software (which has validation checks). Samples of scored booklets are scanned centrally for reliability and trend checks ([TIMSS 2003 Ch. 6][timss03]; [TIMSS 2023 Ch. 8][timss23]).
- India (secondary coaching sites, not official specs): CBSE OMR sheets reportedly allow blue or black ballpoint only (no gel or pencil), require fully darkened bubbles (no ticks or crosses), reject multiple marks, and say the barcode or QR must not be touched ([Careers360][c360]; [PW][pw]).

### Inferences
- Census figures are for adult writers, professionally printed forms and production scanners, with a person keying every uncertain field. Treat about 99% for numbers as the ceiling for design plus human review, not as model-only accuracy on children's pencil photos.
- Isolated boxes (98%) against shared boxes (95–96%) means per-character errors roughly double (2% to 4–5%) when the one-digit-per-box constraint is dropped.
- Per-character accuracy compounds: at 98% per digit, a 3-digit answer is about 94% right as a whole (0.98³). Marking needs whole-answer accuracy, not per-character accuracy.

### Gaps
- The official US Census evaluations of DCS 2000 and of 2010 were not found; the US figures above are the vendor's.
- Not found: evaluations by Statistics Canada or of the ONS 2021 census, the ONS share of fields read automatically, PISA paper data capture, and Indian board or NTA OMR error rates.
- Unverified [snippet]: a [US Census Bureau 2021 working paper][nrp] on reading 1990 forms by machine reportedly found a 3.6% error rate on handwritten IDs (0.6% per character), against 28.8% / 17.5% on typed IDs. The conditions are unknown.

## Q3. Matching a photo or scan to the known page layout: registration marks, QR codes, perspective correction, and page curl

### Takeaway
The standard method finds four or more known marks and computes a perspective correction (a homography) from the photo onto the printed template. Each answer box then sits at known coordinates. Two marks are not enough; four to six well-spread marks work. Tilt, lens distortion and page curl leave leftover error that corner-only correction cannot fix. A QR code reliably identifies the page and can seed the correction, but it should not be the only anchor.

### Cited Findings
- Once the program matches the form's reference marks to the template, "it will know exactly where to look for fields". Standard marks are "more reliable and should always be your first choice" ([ABBYY 2009][abbyy]).
- Census ICR cleans the image before reading: deskew, shift and stretch, contrast, despeckle. Engines typically expect pure black-and-white images ([UN 2009][un]).
- **ArUco marker study** (Štampfl & Ahtik 2022). Setup: printed A4, Nikon D850 DSLR at 82 cm; 22 mm and 15 mm markers; 2, 4, 5 or 6 markers; tilt of 0° or 10° on one or both axes. "Two ArUco markers were insufficient." Four to six markers "provide more consistent alignment". With four, some deviation remains, attributed to lens distortion; the fix is calibration or more markers. Five gave good results at all angles. Six were the most uniform, except with tilt on both axes. Recommendations: six markers at regular intervals, and larger markers, which were "more reliable in most of the tested cases" ([JPMTR 2022][aruco]).
- **BAGS** (Li et al. 2019, smartphone homework grading). Each sheet has four rectangular borderlines for correction and a unique ID at the bottom-left or bottom-right. The ID sits beside a correction corner, so its distortion "would be subtle". A neural network finds the borderlines and a corner detector finds the vertices. Detecting the answer underlines by network reached 76.3% recall / 70.5% precision, against 30–41% recall for Hough and 63–67% for LSD on distorted, cluttered photos ([arXiv:1906.03767][bags]).
- A QR code's three finder patterns (1:1:3:1:1 ratio) plus the missing corner give orientation and enough points for a homography. Alignment patterns (version 2 and up) help stabilise it ([Make Tech Easier, secondary][mte]; [ResearchGate figure][qrfig]).
- **QR read failures on phones:** 11 of 780 Wild-OMR phone captures (about 1.4%) were dropped because the QR was unreadable. Conditions: 5 phones; flat, dim, glare, tilted about 30°, and hand-held curving ([Wild-OMR, Zenodo, 30 Jul 2026][wild]).
- OMRChecker aligns images with marker- or page-crop plugins. Its feature-matching auto-align was deprecated "due to low performance on a generic OMR sheet". Minimum input 640×480 ([OMRChecker][omrc]).
- **Page curl:** DewarpNet (ICCV 2019) "decreas[es] character error rate by 42% on average" on camera-captured documents ([DewarpNet][dewarp]). On the DocUNet benchmark, FDRNet's CER is 16.96%, against 23.95% for DewarpNet and 20.00% for DocTr ([Liner review, secondary][fdr]). These benchmarks are heavily curled printed text, not flat worksheets.

### Inferences
- For the school's sheets: four black squares of 5–8 mm near the corners, plus an asymmetric fifth mark or the QR for orientation. Place the QR next to a corner mark, as BAGS did with its ID, so it can be read before correction.
- For curled or hand-held pages: add marks along the edges, or re-align each answer box locally by searching near its expected position for its printed border. This is an inference, not measured.
- Legacy sheets have no marks. The engine must find the page and locate answers from the printed content (BAGS used a network trained on 9,000 labelled images) or match against a stored blank-sheet image. That extra step can fail.

### Gaps
- No study found reporting alignment error in mm or px for phone photos against flatbed scans of the same form; the ArUco study used a DSLR and a pixel-difference measure. Wild-OMR's results by condition were not on the Zenodo page.

## Q4. Designing for non-numeric answers: tick boxes, bubbles, symbol choices

### Takeaway
Tick marks and bubbles are the most accurately read field type: about 99.85–99.9% in censuses, against about 98.9–99.4% for handwritten numbers and 75–90% for handwritten letters (UN indicative figures). Choice answers (True/False, <, >, =) should be printed options the child marks, not symbols the child writes.

### Cited Findings
- Census tick marks: 99.85% in the 2011 England & Wales census, against 98.93% numeric and 97.58% alphanumeric ([ONS][ons]). In the US 2000 first pass, OMR reached 99.89% against 99.4% for handwriting OCR ([vendor][lm]).
- Letters read at 75–90% and mixed letters and digits "50% or less", against 98% for isolated digits ([UN 2009][un]).
- A checkmark group is a set where exactly one box must be marked. Shapes: square, circle or underline, 3.5–5 mm ([ABBYY 2009][abbyy]).
- The main OMR errors are missing, multiple and partial marks, which go to key correction. Tick boxes don't suit every question, and users need brief instruction ([UN 2009][un]). The 2011 England & Wales census recorded "missing or multi-tick" states and resolved them later ([ONS][ons]).
- Wild-OMR's pencil sheets include scripted erasures and faint marks to test robustness ([Wild-OMR][wild]).

### Inferences
- For "34 __ 43" items, print three option boxes labelled <, >, = to tick. True/False becomes two boxes. Children aged 7–9 may tick rather than fill, so judge how much ink is in each box compared with the others in the same question, not against a fixed threshold. That comparison also handles pencil ghosts from erasures. Flag multi-marks for review.

### Gaps
- Not found: OMR or tick accuracy for children aged 7–9, ticks compared with filled bubbles, or recognition of handwritten <, >, = symbols.

## Q5. Evidence on children's handwriting in boxes (legibility, size, box size)

### Takeaway
No study on box size for 7–9-year-olds, or on how well they keep digits inside boxes, was found. The adult standard is 4×5 mm. Grade 2 numerals are only about 89% legible to trained human raters, and larger letters go with worse handwriting quality. Box size must come from a pilot.

### Cited Findings
- ETCH-Manuscript test, typical second-graders: word legibility 88.82%, letters 84.30%, **numerals 89.26%** ([ResearchGate abstract [snippet]][etch]; authors and sample not confirmed).
- Coradinho et al. 2023: 57 second-graders (mean age 7.25) copied text for 5 minutes on A4 over a digitising tablet. Median vertical size was 0.17 cm (IQR 0.13) at age 7 and 0.23 cm (IQR 0.22) at age 8. Larger size was "strongly associated with worse handwriting quality" (r = 0.50–0.63) ([PMC10047900][cor]).
- Adult cells are 4×5 mm; larger cells encourage "abnormally large letters" ([ABBYY 2009][abbyy]). "There will be a limit to the capability of the chosen system due to the quality of handwriting" ([UN 2009][un]).

### Inferences
- If about 11% of Grade 2 numerals are illegible even to trained raters (ETCH), census-level digit accuracy is out of reach. Constrained boxes, and knowing the expected answer for each question, matter more for children than for adults.
- Following ABBYY's rule to match the cell to natural letter size suggests cells well above 4×5 mm for Grade 2, perhaps 8–10 mm. Pilot several sizes and measure how often children write over the border. This is untested.

### Gaps
- Not found: box-size studies for children, how often children write over borders, or any benchmark of ICR on children's boxed digits. MNIST-style data comes from adults and high-school students.

## Q6. Phone-capture guidance: how apps make photos usable

### Takeaway
Current capture tools find the page edges, take the photo automatically when the page is detected, correct rotation and perspective, and remove shadows. Exam platforms add a QR code per page to match pages to students and to flag missing pages. No documented blur-rejection thresholds were found.

### Cited Findings
- Google ML Kit Document Scanner (on-device): "Automatic capture with document detection", "Accurate edge detection for optimal crop results", "Automatic rotation detection". Also filters, shadow removal, and ML removal of stains and fingers. Developers can cap page count and disable gallery import ([ML Kit docs][mlkit]).
- Gradescope app [snippet]: "will scan pages automatically when you hold your phone above each page". Pages can be re-cropped or rotated. Tips: work on a flat surface, and "do not crop off parts of the assignment page if you are using a provided assignment document" ([Gradescope app guide][gs1]; [Gradescope scanning tips][gs2]; [Stanford tips PDF][gs3]).
- Crowdmark [snippet]: a QR code on every page. Uploads are split into student booklets by QR code, with errors listed for fixing. A missing page shows "a red band and a warning". Re-uploads replace images by QR match without disturbing grading. The Exam Matcher app links a booklet to a student by scanning a page's QR ([upload][cm1]; [QR cheat sheet][cm2]; [Exam Matcher][cm3]).
- BAGS uploads in greyscale "for transfer efficiency" ([BAGS][bags]). The ONS pipeline gates on an automatic image check (size, barcodes present) with a person handling failures ([ONS][ons]). The US 2000 census rescanned 0.8% of forms ([vendor][lm]).

### Inferences
- Gate each upload before accepting it: (1) the QR decodes (about 1–2% of phone photos failed in Wild-OMR); (2) all corner marks are found and the corrected shape is close to A4; (3) a sharpness score passes a threshold tuned on the school's own photos. Reject while the sheet is still in hand, because a re-shoot costs less than a wrong reading. Keep the corner marks in frame, per Gradescope's "don't crop the template" advice.

### Gaps
- No published blur, glare or resolution thresholds were found for Gradescope, Crowdmark, VisionKit or ML Kit.

## Q7. Measured accuracy: handwriting in boxes vs free layout, and OMR on scans vs phones

### Takeaway
No controlled study compares the same children's answers on a designed sheet and on a legacy sheet. The evidence lines up as follows:
- Designed census forms reach about 99% for numbers, after human review.
- Digits in their own boxes read at 98% per character, against 95–96% in shared boxes.
- A phone-photo homework system with answers on underlines read 91% of answers fully right.
- One open-source OMR tool claims about 100% on scans and about 90% on phone photos.

Design removes most failures to find the answer and roughly halves per-character reading errors. It does not remove the limit set by children's legibility.

### Cited Findings
**Boxed vs less constrained**
- Per character: 98% isolated vs 95–96% semi-constrained numeric; 90% upper case; 75–80% mixed case ([UN 2009][un]).
- ONS 2011, designed form, adult writers, after keying: numeric 98.93%, year of birth 100.00%, alphanumeric 97.58%, marks 99.85% ([ONS][ons]).
- Morocco 2004: automatic reading 3.56–3.57 errors per 10,000 against 19.95 for keying ([UN 2009][un]).
- Vendor blogs with no stated method:
  - Apryse: "neat printing in form boxes" 90–95%, "average everyday handwriting" 80–90% ([Apryse][apryse]).
  - ImageToTable (low-quality source): block capitals in boxes 75%+ per field with classic ICR against under 50% for cursive in free fields; with vision models, 90–97% against 65–85% ([ImageToTable][itt]).

**Free-layout school work**
- BAGS (2019): phone photos, answers on underlines, 4 borderlines plus an ID; answer-finding trained on 9,000 labelled images, reading on 860,000 answer images. On 383 test photos (6,068 answer areas), over 91% were fully right and under 5% failed (edit-distance accuracy under 0.9). Of 274 failures, 52 came from answer-finding, 68 from misreading, and 154 from "ambiguous handwriting or low-quality images" ([arXiv:1906.03767][bags]).
- Henkel et al. (Oct 2025): multimodal LLMs grading 288 handwritten arithmetic answers from Ghanaian middle-school students reached "near-human accuracy (95%, κ = 0.90)". For 150 US elementary students' drawings, κ was 0.20, rising to 0.47 with human descriptions ([arXiv:2510.05538][henkel]). A search summary said 98%; the abstract says 95%.
- Pather et al. (Apr 2026): 17 multimodal LLMs on a real handwritten medical form. Best about 85% accuracy (weighted F1 ≈ 90%). Lowest hallucination rate 6% (GPT 5.4). Claude Sonnet 4.6 best on dates and numbers. Best free-text result WER 0.50 / CER 0.31 (Gemini 3.1) ([arXiv:2604.16504][pather]).

**OMR: scan vs phone**
- OMRChecker claims "nearly 100% accurate on good quality document scans and about 90% accurate on mobile images". This is the developer's claim; the metric and test set are not stated ([OMRChecker][omrc]).
- Wild-OMR (2026) was built to measure accuracy lost to phone capture. Design: 30 pencil sheets × 200 bubbles, 5 phones (2019–2026 models), 5 conditions, a 300-dpi flatbed reference, and 8 readers. Results by condition were not on the record page ([Wild-OMR][wild]).
- Production census OMR: 99.85% (ONS 2011), 99.89% (US 2000, vendor), and a 99.5–99.99% supplier range ([ONS][ons]; [LM][lm]; [UN][un]).

### Inferences
- **What design fixes.** About 19% of BAGS failures (52/274) were failures to find the answer, which fixed boxes plus corner marks largely remove. One-digit boxes roughly halve per-character error. The biggest failure group, "ambiguous handwriting or low-quality images" (56% of BAGS failures), is reduced only by capture-quality checks and human review.
- **Rough accuracy bands for this school (extrapolated, not measured).**
  - Designed sheet (QR plus marks, one-digit boxes, choice boxes for symbols, low-confidence answers sent to a person): about 97–99% of answers right after review, bounded by Grade 2 legibility.
  - Legacy sheet read by a model alone: about 90–95% per answer (BAGS 91%, Henkel 95%).
  - Replace both bands with the school's own evaluation.
- Vision-language models narrow the free-layout gap. They also hallucinate: at best 6% in Pather et al. Classic ICR does not do this. Constrained fields (a known box, an expected digit count) make range checks easier and help catch it.

### Gaps
- No controlled study found comparing boxed and free layout for the same writers, let alone children. No figures found on alignment accuracy for phones versus flatbed scans. Wild-OMR's per-condition results, the most directly useful phone-vs-scan OMR figures, were not retrievable.

[abbyy]: https://static1.abbyy.com/abbyycommedia/4673/abbyy-flexicapture-80-form-creation-guide.pdf
[abbyy12]: https://help.abbyy.com/en-us/flexicapture/12/standalone_administrator/ap_mrf_types_color/
[un]: https://unstats.un.org/unsd/demographic-social/census/documents/CensusDataCaptureMethodology.pdf
[ons]: https://www.ons.gov.uk/file?uri=%2Fcensus%2F2011census%2Fhowourcensusworks%2Fhowdidwedoin2011%2F2011censusgeneralreport%2F2011censusgeneralreportforenglandandwaleschapter5_tcm77-384969.pdf
[lm]: https://news.lockheedmartin.com/2001-01-08-Lockheed-Martins-Data-Capture-System-Processes-148-Million-Census-Forms-With-Record-Speed-and-Accuracy
[para]: https://www.parascript.com/blog/handprint-recognition-beyond-boxes-combs/
[naep1]: https://nces.ed.gov/nationsreportcard/contracts/item_score.asp
[naep2]: https://nces.ed.gov/nationsreportcard/tdw/process_materials/
[timss03]: https://timssandpirls.bc.edu/PDF/t03_download/T03_TR_Chap6.pdf
[timss23]: https://timss2023.org/wp-content/uploads/2024/11/T23_TR_Chap8.pdf
[c360]: https://school.careers360.com/boards/cbse/cbse-omr-sheet-2026
[pw]: https://www.pw.live/neet/exams/neet-2026-omr-filling-instructions
[nrp]: https://www.census.gov/content/dam/Census/library/working-papers/2021/econ/1990_NRP2.pdf
[aruco]: https://doi.org/10.14622/JPMTR-2216
[bags]: https://arxiv.org/abs/1906.03767
[mte]: https://maketecheasier.com/mte-a-qr-codes-three-corner-squares-arent-decoration-theyre-position-markers-that-let-a-scanner-work-out-the-codes-orientation-in-under-a-millisecond-even-when-you-photograph-it-upside-down-or-at-45-d/
[qrfig]: https://www.researchgate.net/figure/Finder-Patterns-and-Alignment-Pattern-in-QR-Code_fig2_261235397
[wild]: https://zenodo.org/records/21710005
[omrc]: https://github.com/Udayraj123/OMRChecker
[dewarp]: https://sagniklp.github.io/dewarpnet-webpage/
[fdr]: https://liner.com/review/fourier-document-restoration-for-robust-document-dewarping-and-recognition
[etch]: https://www.researchgate.net/publication/336601860_Handwriting_Performance_of_Typical_Second-Grade_Students_as_Measured_by_the_Evaluation_Tool_of_Children's_Handwriting_-_Manuscript_and_Teacher_Perceptions_of_Legibility
[cor]: https://pmc.ncbi.nlm.nih.gov/articles/PMC10047900/
[mlkit]: https://developers.google.com/ml-kit/vision/doc-scanner
[gs1]: https://guides.gradescope.com/hc/en-us/articles/22016028459789-Using-the-Gradescope-Mobile-App-for-Students
[gs2]: https://guides.gradescope.com/hc/en-us/articles/21707758815245-Scanning-Tips
[gs3]: https://web.stanford.edu/~lmackey/stats202/misc/gradescope_tips.pdf
[cm1]: https://www.crowdmark.com/help/fixing-errors-in-assessment-upload/
[cm2]: https://crowdmark.com/help/administered-assessment-cheat-sheet/
[cm3]: https://www.crowdmark.com/help/what-is-the-exam-matcher-app/
[apryse]: https://apryse.com/en-ca/blog/handwriting-icr-guide
[itt]: https://imagetotable.ai/blog/handwritten-pod-extraction-accuracy-guide
[henkel]: https://arxiv.org/abs/2510.05538
[pather]: https://arxiv.org/abs/2604.16504
