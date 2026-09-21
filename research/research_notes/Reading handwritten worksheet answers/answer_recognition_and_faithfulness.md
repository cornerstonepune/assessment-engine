# Recognising a child's short handwritten answer once located, and keeping the reader faithful to what was written

Scope note for the report writer: every number below carries its dataset and conditions. "Exact match" = the whole answer string is right; "CER" = character error rate. Most 2026 items are arXiv preprints (not yet peer-reviewed). Older (pre-2023) results are flagged with their year. Three WebFetch summaries in this session named systems (e.g., "Amazon Textract") that the underlying papers do not contain; I checked each paper's full text with pdftotext and included only claims that appear in it.

## 1. Per-box recognisers for digits and short answers (CNN, CRNN/CTC, TrOCR, PARSeq, Donut): accuracy, especially on children's handwriting

### Takeaway
A dedicated recogniser works well when trained on the target population's own crops. Trained elsewhere, it degrades badly. A TrOCR fine-tuned on 500 in-domain handwritten number cells reached 95% exact match, 97.2% with 5k cells and 98.7% with 7k cells plus bank-cheque digits. Confidence-based rejection raised it to 99.4%. In contrast, models trained only on MNIST/EMNIST or cheque data scored between 5% and 71% on real form crops. No public dataset of children's handwritten digits or Grade 2-4 answers with published exact-match results turned up. The nearest are AEC-5k (Chinese primary-school arithmetic, 2020), an elementary-school handwriting line set (E-TrOCR, 2025) and Ghanaian middle-school arithmetic sheets (2025).

### Cited Findings
- **TrOCR fine-tuned on handwritten number cells (Bhaskar et al., COMPASS '25, June 2025).** The data is 1930s property cards with handwritten 3-5 digit valuations, cropped to single cells. Pre-trained TrOCR and Tesseract "would often confuse letters and digits, including recognizing the digit 0 with the letter O and the digit 1 with lowercase L or uppercase I." Exact-match results after fine-tuning (Table 7):
  - own data n=500: 95%
  - CAR-B cheque digits n=3k only: **4.90%**
  - own data n=5k: 97.17%
  - own data n=7k combined with CAR-B n=3k: 98.69%
  - CAR-B first, then own data: 95.51%

  Blank outputs "are usually accompanied by a low confidence score," and "by choosing an appropriate threshold, we can achieve an exact match accuracy of up to 99.4%." The paper does not state the exact coverage at that point; its table reports top-90/95/99% retention. Tesseract retrieved the correct value in only 52.5% of test cases. Azure Document Intelligence reached about 94% OCR accuracy but found table cells poorly (about 78%). — [Bhaskar et al. 2025, arXiv 2505.24676](https://arxiv.org/pdf/2505.24676)
- **Same paper, GPT-4o on cropped cells.** "When using the ChatGPT API in a more constrained setting — such as OCR on cropped subsections of the card after segmentation (e.g., individual cell value), the accuracy of OCR matches or exceeds that of the fine-tuned TrOCR model." On multi-cell or whole-card input, GPT-4o was "hit-or-miss", sometimes "hallucinating to give partial results." — [Bhaskar et al. 2025](https://arxiv.org/pdf/2505.24676)
- **EMNIST-trained classifiers on real exam crops (Grabowski, 2023).** The task was single capital letters in exam answer tables: 2,646 cells from 49 exams. Results by pipeline:
  - fixed-cell cropping + EMNIST CNN: 70.75%
  - YOLOv5 cell cropping + CNN: 65.50%
  - YOLOv5 detect+classify trained on EMNIST: 84.46%
  - YOLOv5 trained on a customised synthetic-form dataset: 88.28%

  14% of letters were written outside the cell "because the user corrected himself." EMNIST's label space causes O/0 and I/L confusions. — [Grabowski, arXiv 2606.08858 (preprint of IFIP 2023 chapter)](https://arxiv.org/pdf/2606.08858)
- **VLMs vs detectors on the same exam-letter task (Grabowski, June 2026).** The benchmark is 61 exams, 742 pages, 3,141 answer positions, and the model sees the whole page. With no hint, accuracy was:

  | Reader | Accuracy |
  |---|---|
  | Gemini 3.1 Flash-Lite | 97.61% |
  | Gemini 3.5 Flash | 97.77% |
  | Qwen3-VL-30B | 93.92% |
  | GPT-5.2 | 93.57% |
  | Grok-4.3 | 89.59% |
  | YOLOv5 | 90.93% |
  | YOLO26 | 89.18% |

  VLMs recovered cases that detectors cannot: letters placed outside the cell, crossed-out plus rewritten answers, cursive glyphs, and an "F" whose lower stroke touches the cell border being read as "E". — [Grabowski 2026, arXiv 2606.11477](https://arxiv.org/pdf/2606.11477)
- **Multi-digit string recognition, classic benchmarks (older, flagged).** Hochuli et al. (2020) compared end-to-end YOLO, RetinaNet and CRNN digit-string recognisers. Best string-level rates: NIST SD19 97%, ORAND-CAR 96%, CVL 84%. YOLO "compares favorably against segmentation-free models"; segmentation-free models struggled with many touching digits. — [Hochuli et al. 2020, arXiv 2010.15904](https://arxiv.org/abs/2010.15904). An earlier ResNet+RNN-CTC model (2017) reached 95.41% (CAR-A), 95.90% (CAR-B) and 88.06% (CVL, about 300 writers). — [arXiv 1710.03112](https://arxiv.org/pdf/1710.03112); dataset facts via [ResearchGate summary](https://www.researchgate.net/publication/344957159_A_Comprehensive_Comparison_of_End-to-End_Approaches_for_Handwritten_Digit_String_Recognition)
- **Primary-school arithmetic (older, 2020).** AEC-5k has 5,300 images from 40 mainstream exercise types covering all primary grades, with printed and handwritten text mixed. The Arithmetical Exercise Checker scored 93.72% "correction accuracy" on its test set, pre-trained on a 600k synthetic handwritten-expression corpus. — [Hu et al., AAAI 2020](https://ojs.aaai.org/index.php/AAAI/article/view/5410)
- **Children's handwriting HTR (2025).** E-TrOCR is a TrOCR fine-tuned first on IAM, then on a child-handwriting set of more than 1,800 text lines from elementary-school students. The authors say child handwriting characteristics "are rare in adult handwriting" and that "current models often autocorrect or misinterpret these features." A related source reports CER of 1.75% on adult samples vs **3.48% on child samples**. I could not open the full text (NSF PAR refused connections; Springer is paywalled), so this adult-vs-child figure is unverified in context. — [From Scribbles to Text, Springer 2025](https://link.springer.com/chapter/10.1007/978-3-032-04614-7_7); [NSF PAR copy](https://par.nsf.gov/servlets/purl/10653115)
- **Children's Arabic characters (not digits).** A confidence-weighted CNN stacking ensemble reached 95.13% on Hijja and 96.14% on Dhad. — [PMC12736956](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12736956/)
- **Handwritten maths expressions.** At the ICDAR 2023 CROHME competition, one team won all three tasks (on-line, off-line, bimodal) with more than 80% expression recognition rate. The training set had 10,979 images and the test set 2,300. — [CROHME 2023, Springer](https://link.springer.com/chapter/10.1007/978-3-031-41679-8_33)
- **General HTR leaderboards (aggregator, lower confidence).** One aggregator lists IAM CER of about 1.22% (GPT-5), about 1.31% (Claude Opus 4.7), about 1.44% (Gemini 3), and about 1.8% for Azure Document Intelligence v4.0. These are line-level CER on adult English text, not exact match. — [CodeSOTA (aggregator)](https://www.codesota.com/ocr/best-for-handwriting)

### Inferences
- The engine's current Textract behaviour (fragments like '2' for '72', low confidence on legible digits, sensitivity to margins) resembles general-purpose OCR on isolated numeric crops. Bhaskar et al. saw the same class of problem with pre-trained models, and in-domain fine-tuning on a few thousand crops fixed it.
- The CAR-B-only result (4.9% exact match) shows that "digit data from somewhere else" does not transfer. The recogniser must see this school's children's pencil on this worksheet's paper.
- Both a fine-tuned small model and a crop-level VLM can plausibly reach the ≥95-97% exact-match target. Neither reaches ≤1% confidently wrong without a rejection or agreement layer (see Q3).

### Gaps
- No published exact-match results found for PARSeq or Donut on handwritten digit strings or short handwritten answers. PARSeq results are scene-text only.
- No public children's handwritten-digit dataset (Grade 2-4) with published recogniser accuracy was found.
- Could not verify the E-TrOCR CER table from the full text.
- No peer-reviewed measurement of Amazon Textract on isolated handwritten digit crops was found. Aggregator blogs (e.g., a "70% on handwriting" claim) are not reliable enough to cite as fact.

## 2. Vision-language models on handwriting and handwritten-maths reading: accuracy and documented "auto-correction"

### Takeaway
Frontier VLMs read handwriting well on average. Their errors, though, are disproportionately driven by what the model expects rather than by what it sees. On handwritten maths solutions containing deliberate errors, **42-66% of VLM transcriptions overwrote at least one of the student's errors**. Larger models in a family over-corrected more, and prompting against it helped only marginally. The engine's 397→387 failure is this documented behaviour, not a one-off.

### Cited Findings
- **Over-correction on handwritten maths (Seong et al., arXiv 2604.22774, v2 May 2026).** The data is FERMAT: 2,244 handwritten samples from 609 problems with deliberately introduced errors. Of 15 VLMs tested, "42–66% of transcriptions contain at least one instance where the model overwrites the student's original work." Per model: Qwen2.5-VL-32B 66.2% (highest), LLaMA-3.2-11B 42.1% (lowest), Gemini 2.5 Flash about 43%, GPT-4o about 55%.
  - Mechanism, in the authors' example: an erroneous "5" in "2 × 3 = 5" conflicts with "the powerful internal context that implies the token in that spot must be '6'."
  - Within a family, larger models over-correct more. Attention maps show less attention to the error region in over-correcting models.
  - Critical-level rewrites occurred; one GPT-4o case inflated a rubric score from 14 to 100.
  - Explicit "don't correct" prompts gave "marginal reduction" while degrading transcription accuracy. The authors conclude over-correction is "deeply entangled with the models' core reasoning capabilities."
  - A BLEU leaderboard flips under their faithfulness metric (PINK): Gemini 2.5 Flash goes from 10th to 1st (PINK 0.935); GPT-4o goes from 3rd to 6th (0.907).

  — [Seong et al. 2026](https://arxiv.org/html/2604.22774v2)
- **Prior-driven errors vs humans (WildHandBench, Aug 2026).** The benchmark has 500 real handwritten documents (text, tables, formulas; Chinese and English), 18 models, including Claude Opus 4.8 and Gemini 3.1 Pro. Best model Gemini 3.1 Pro scored 71.85% overall vs a human baseline of 77.09%. A "prior-driven error" is an output the language model finds more probable than the ground truth. Such errors made up **63-91% of model errors** (Gemini 3.1 Pro 77.51%) vs **49.27% for humans**, who stay "conservative on illegible content." — [WildHandBench, arXiv 2608.22959](https://arxiv.org/html/2608.22959)
- **Do VLMs read or rewrite? (Lee et al., Amazon, arXiv 2607.21617, Sept 2026).** Printed documents had about 5% of characters perturbed; 15 systems were tested. Rewriting rates for scrambled words:

  | System | Share of perturbed words rewritten |
  |---|---|
  | olmOCR-2-7B | 58.63% |
  | LightOnOCR-2-1B | 53.69% |
  | InternVL3.5-4B | 46.37% |
  | Qwen3-VL-4B | 31.33% |
  | Gemini-3-Flash | 0.00% |
  | Tesseract | 0.00% |

  Short words (4-6 characters) were rewritten 7.6-10.0% of the time, dropping to 0% at 8+ characters. Corrupting 5% of characters caused a 7.3× error increase on the *unperturbed* text (Qwen3-VL-4B). — [Lee et al. 2026](https://arxiv.org/html/2607.21617)
- **Ghanaian middle-school arithmetic worksheets (Henkel et al., arXiv 2510.05538, 2025).** The data is 288 handwritten responses. One prompt showed the whole worksheet, including printed problems, and asked the model to transcribe the "exact final answer" *and* judge correctness in the same call.

  | Model | Reading ("vision") accuracy | Grading accuracy |
  |---|---|---|
  | Claude 3.5 Sonnet | 79% | 77% |
  | Claude 3.7 | 76% | 84% |
  | Gemini 2.5 Pro | 89% | 95% (κ=0.90) |
  | GPT-4.1 | 86% | 79% |

  The authors: models with grading above reading "may use mathematical context to compensate for imperfect visual interpretation … this raises concerns about false positives." Human-to-human agreement "approached 100%." The paper's text and its confusion-matrix column labels disagree on which column is false positives. — [Henkel et al. 2025](https://arxiv.org/pdf/2510.05538)
- **University handwritten maths (Levine et al., UIUC, May 2026).** 600 photographed submissions were graded by GPT-5-mini, GPT-5.1 and Gemini-3-flash with problem, rubric and reference solution in one prompt. 87% of grading errors came from transcription failures. Models "occasionally hallucinated text not present in submissions, sometimes resembling reference solutions and inflating scores," especially on blurry or rotated images. — [Levine et al. 2026, arXiv 2605.19043](https://arxiv.org/html/2605.19043v1)
- **Handwritten medical forms (Pather et al., arXiv 2604.16504, Apr 2026).** 49 real forms mixing checkboxes, numbers, dates and free text were read at temperature 0 with a JSON template.

  | Model | Median accuracy on numbers and dates, excluding empty fields | Hallucination rate |
  |---|---|---|
  | Claude Sonnet 4.6 | 77% (best) | 12% |
  | Haiku 4.5 | 73% | 23% |
  | GPT-5-mini | 72% | 17% |
  | Gemini 3.1 Flash-Lite | 72% | 8% |
  | Gemini 3.1 Pro | 67% | 8% |
  | Opus 4.6 | not reported | 10% |
  | GPT-5.4 | not reported | 6% (lowest) |

  "When individual fields … cannot be interpreted, models do not flag uncertainty. They will either return a blank value, infer the closest plausible alternative, or hallucinate some output entirely." Models also defaulted to full stops as decimal separators regardless of the source — a formatting prior. — [Pather et al. 2026](https://arxiv.org/pdf/2604.16504)
- **LLM-based HTR benchmark (Crosilla et al., 2025).** Proprietary models, "especially Claude 3.5 Sonnet," beat open-source ones zero-shot on modern handwriting, with "no consistent advantage" over Transkribus models. LLMs showed "limited ability to autonomously correct errors" in their own transcriptions. — [Crosilla et al., arXiv 2503.15195](https://arxiv.org/abs/2503.15195)
- **General OCR hallucination literature.** The "OCR hallucination" phenomenon — over-reliance on language priors — is benchmarked by HalluText ([OpenReview](https://openreview.net/forum?id=LRnt6foJ3q)) and KIE-HVQA ([NeurIPS 2025](https://papers.nips.cc/paper_files/paper/2025/file/6b628a3d7cb8055eb6fd2dd48c586347-Paper-Conference.pdf)). Output logits in VLMs "are often severely miscalibrated." — [Yao et al. 2025, arXiv 2511.19806](https://arxiv.org/pdf/2511.19806)

### Inferences
- Three conditions together produce the engine's failure: the question visible, a short numeric token, and a strong model. That combination is exactly where the literature finds rewriting peaks: context-implied tokens (FERMAT), short strings (Lee et al.), and larger or reasoning-heavier models (Seong; Pather's note that "advanced reasoning may sometimes be detrimental").
- Claude models were the weakest *readers* in the one children's-arithmetic study (76-79%). Claude 3.7's grading exceeding its reading by 8pp fits "answering from context." This is consistent with the engine's experience, but it is one small study (288 responses).
- Model choice matters by family. Gemini-3-Flash showed 0% rewriting in Lee et al.; Gemini 2.5 Flash had the lowest over-correction among top performers in FERMAT. That is 2 of 2 independent studies favouring Gemini Flash for faithfulness, but neither used children's digit crops.

### Gaps
- No study measured VLM over-correction on *cropped single numeric answers* from children with the question hidden. All over-correction measurements include surrounding context.
- No published handwriting-OCR numbers were found for Claude 4.x/5 on digit crops specifically.

## 3. Techniques that keep a reader faithful: crop-only, literal-transcription prompts, constrained output, temperature 0, multi-reader agreement, self-consistency, re-rendering — with measurements

### Takeaway
Measured evidence ranks the levers:
1. **Never give the reader the question or the expected answer.** Doing so measurably converts wrong answers into "correct" readings.
2. **Use agreement between independent readers of different kinds (different model families and OCR engines) to decide when to accept.** This beat single-model self-consistency and VLM-as-judge.
3. **Use rejection on confidence or disagreement.** It trades coverage for precision.

Literal "don't correct" prompts help only partly: 33-47% less rewriting in one study, "marginal" in another, and both at some accuracy cost. Chain-of-thought gave little benefit. No published measurement of "verify by re-rendering" for handwriting was found.

### Cited Findings
- **Giving the expected answer causes wrong answers to be read as right (Grabowski 2026).** Same 3,141-position exam benchmark. In "weak-hint" mode the model is told "the expected letters are …". False positives (a wrong answer read as the correct one), counts out of 3,141:

  | Model | Plain | Weak-hint |
  |---|---|---|
  | Grok-4.3 | 1 | 193 (specificity 0.74) |
  | GPT-5.2 | 5 | 80 |
  | Qwen3-VL-30B | 4 | 32 |
  | Gemini 3.1 Flash-Lite | 1 | 11 |

  False negatives dropped (Gemini 52→14; GPT-5.2 144→27), because the author optimised for not penalising students. The author names this a "hint bias in which the model over-trusts the provided reference and accepts wrong answers." Running both modes and flagging disagreements is proposed as a "four-eyes (dual-configuration) check." — [Grabowski 2026](https://arxiv.org/pdf/2606.11477)
- **Reference solutions leak into transcriptions (Levine et al. 2026).** Hallucinated text "sometimes resembling reference solutions and inflating scores." The single-call design put problem, rubric and reference in the same prompt as the image. — [Levine et al. 2026](https://arxiv.org/html/2605.19043v1)
- **Literal-transcription prompt (Lee et al. 2026).** Prompt: "Transcribe everything exactly as it appears—do not correct or fix any words." On Qwen3-VL-4B (English), degradation fell 47% (scramble), 35% (visual) and 33% (random). Clean-text WER rose from 0.29% to 0.66%. Chain-of-thought gave "minimal additional benefit." — [Lee et al. 2026](https://arxiv.org/html/2607.21617)
- **Anti-correction prompt on handwritten maths (Seong et al. 2026).** "Marginal reduction but simultaneously degraded transcription accuracy—no net improvement." — [Seong et al. 2026](https://arxiv.org/html/2604.22774v2)
- **Multi-VLM agreement ("Consensus Entropy", Zhang et al., arXiv 2504.11101 v4, 2026).** The method measures pairwise normalised edit-distance agreement across several VLMs' OCR outputs and accepts low-disagreement outputs.
  - Error-detection F1 48.0-51.3 vs 36.1-40.0 for VLM-as-judge.
  - Routing only the high-disagreement 7.3% of samples to a stronger model gave +8.2% on OCRBench vs the best single model.
  - Self-consistency with 3 samples of one model gave only +2.7%.
  - Classic character-level voting (ROVER) failed badly on Math-VQA (−92%).

  — [Zhang et al.](https://arxiv.org/html/2504.11101v4)
- **Why single-model confidence is weak (Yao et al., Nov 2025).** Token-probability confidence is miscalibrated. Self-consistency and semantic entropy "are not applicable to free-form answers since OCR requires character-level precision." Probing hidden states (open-weight models only) improved abstention accuracy by 7.6% over the best baseline. — [Yao et al., arXiv 2511.19806](https://arxiv.org/pdf/2511.19806)
- **Confidence rejection on a fine-tuned recogniser (Bhaskar et al. 2025).** Thresholding TrOCR confidence raised exact match to "up to 99.4%." Keeping the most confident 90% of predictions gave 94.68% within 5% of true value vs 85.37% keeping all, a regression metric rather than exact match. — [Bhaskar et al. 2025](https://arxiv.org/pdf/2505.24676)
- **Crop-only VLM reading (Bhaskar et al. 2025).** GPT-4o was reliable on single cropped cells with a plain "Perform OCR" prompt and unreliable on multi-cell regions (partial or hallucinated outputs). — [Bhaskar et al. 2025](https://arxiv.org/pdf/2505.24676)
- **Temperature 0 and JSON templates.** These were used in the forms benchmark, but hallucination rates stayed at 6-23%. Deterministic, structured output did not stop fabrication. — [Pather et al. 2026](https://arxiv.org/pdf/2604.16504)
- **Restricting the character set.** Pre-trained general OCR confused 0/O and 1/l/I; digit-focused fine-tuning fixed it. — [Bhaskar et al. 2025](https://arxiv.org/pdf/2505.24676). EMNIST label-space confusions (O/0, I/L) are also reported by [Grabowski 2023/2026](https://arxiv.org/pdf/2606.08858).
- **Ensembles of independent graders, and hiding the reference image (Perš et al., Jan 2026).** For handwritten engineering exams, they used an ensemble of independent MLLM graders plus a supervisor, and converted the reference solution to text "without exposing the reference scan." Result: about 8-point mean absolute difference to lecturer grades, with about 17% of answers routed to manual review. That was a *grading* task: removing the reference *degraded* grading. — [Perš et al., arXiv 2601.00730](https://arxiv.org/abs/2601.00730)

### Inferences
- For a read-then-grade engine, separate reading from grading completely. The reader gets only the answer crop and no question, operands or expected value. The grader compares afterwards in code. The weak-hint numbers show that even a one-line hint makes some models accept wrong answers at scale (GPT-5.2: 80 of 3,141). A bare expected value in the prompt is the most direct form of the problem.
- Accept a reading only when two readers of different kinds agree exactly — e.g., Textract plus a crop-level VLM, or plus a fine-tuned digit model. Route disagreements to a teacher. Consensus Entropy supports cross-model disagreement as a better error flag than asking one model to re-sample or judge itself. The acceptance rate (coverage) then becomes the metric to tune against "≤1% confidently wrong."
- A "grading-consistency" tripwire follows from Henkel's finding. If a VLM reading equals the arithmetically correct answer while an independent OCR reads something else, treat that as a known correction pattern and send it to review rather than accepting it. This is an inference, not a published technique.
- Verifying by re-rendering the reading and comparing images has no published handwriting evidence. Treat it as experimental.

### Gaps
- No study measured per-character alternatives ("list possible readings of each digit") as a faithfulness technique.
- No published measurement found of crop-only vs with-question VLM reading on identical handwritten numeric answers. This is the single most useful experiment the engine could run on its own data.
- No measurement found of Textract + VLM agreement specifically.

## 4. Human baselines: how accurately do people read children's (and adults') handwritten answers?

### Takeaway
On clear arithmetic answers, trained humans agree nearly perfectly after discussion. Clean isolated digits carry about 0-2.5% human error depending on dataset difficulty. Single-pass manual keying of handwritten numbers carries measurable error, sometimes several percent, and double-entry halves it. Humans also err differently from models: they leave illegible content unresolved rather than filling it from expectation.

### Cited Findings
- **Isolated digits (older, flagged).** On the USPS test set, "two humans made errors at an average rate of 2.5%." Human error on NIST SD-7 was 1.5%. Best machine error on MNIST is about 0.17-0.25%. — [Wikipedia: MNIST database (citing original sources)](https://en.wikipedia.org/wiki/MNIST_database). A human error rate of about 0.2% on MNIST also circulates in search results, but I did not verify it on a primary page.
- **Middle-school arithmetic answers.** "Human-to-human agreement approached 100%"; the few disagreements concerned whether simplified forms count and scratched-out vs final answers. On elementary students' maths *illustrations*, expert teachers agreed only about 76% (linear weighted κ 0.45). — [Henkel et al. 2025](https://arxiv.org/pdf/2510.05538)
- **Handwritten documents, WildHandBench.** Humans scored 77.09% under the benchmark protocol vs 71.85% for the best model. Human errors were prior-driven 49.27% of the time vs 63-91% for models. — [WildHandBench 2026](https://arxiv.org/html/2608.22959)
- **Handwritten numbers on property cards.** Two authors and three contractors annotated the same sample; "the disagreement was below 0.02 for every pair of annotators." — [Bhaskar et al. 2025](https://arxiv.org/pdf/2505.24676)
- **Survey marks.** Inter-annotator Cohen's κ = 0.91 on tick, circle, cross and bubble marks (SurveySet). — [Quiñones et al. 2026, PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC13117292/)
- **Manual data entry (older, 2012).** Paulsen et al. covered 398 questionnaires with 21,887 fields.
  - Checkbox fields, errors per 1,000: single-key 3.70; double-key 0.46; automated forms processing 0.46.
  - Hand-printed number fields (EQ-VAS, n=297), errors per 1,000: single-key 67.34; double-key 33.67; automated forms processing 101.01 (about 10%).

  The automated processing included manual validation of ambiguous entries: 0.25-20.2% of fields depending on questionnaire, highest (20.2%) for the handwritten-number field. "It is clearly more difficult for the AFP system to identify a hand-printed character (number) correctly than to identify if a check box is marked." — [Paulsen et al., PLoS ONE 2012](https://pmc.ncbi.nlm.nih.gov/articles/PMC3320865/). The confidence intervals reported on the page do not match the per-1,000 units, so treat the point estimates as the reliable part.
- **Clinical data-entry range.** Single-entry error rates ranged 4-650 per 10,000 fields; double-entry 4-33 per 10,000. The CAST trial: 22 vs 15 per 10,000. — [Research Square review](https://www.researchsquare.com/article/rs-2386986/v1.pdf); [CAST, PubMed](https://pubmed.ncbi.nlm.nih.gov/1334820/)
- **Grading agreement (not reading).** On FERMAT, three expert annotators had weighted κ 0.69 when scoring transcriptions. — [Seong et al. 2026](https://arxiv.org/html/2604.22774v2)

### Inferences
- A realistic human benchmark for "read the child's final number" is about 99-100% after adjudication. A single unaided teacher pass likely has a small but non-zero error, on the order of the 0.2-2.5% isolated-digit figures. So ≥97% exact reading with ≤1% confidently wrong is roughly single-marker level. Beating double-marking would need agreement plus review.
- The most transferable human behaviour is that people say "can't read it" instead of guessing. That supports designing an explicit "illegible/unsure" output and routing it to review.

### Gaps
- No inter-rater study specifically on teachers reading Grade 2-4 children's handwritten numbers was found.

## 5. How much data adapts a recogniser to a population's handwriting; do per-writer (per-child) profiles help?

### Takeaway
Population-level fine-tuning is the big lever: hundreds to a few thousand labelled in-domain crops move a recogniser from unusable to 95-98.7% exact match. Per-writer adaptation helps, but by smaller relative amounts: about 5% from 1 line, 10-20% from 2-8 lines, 20-45% from 16-256 lines, with the published relative figures ranging from 20-25% (16 lines) to 45-50% (256 lines) depending on the source. Parameter-free in-context writer adaptation gives modest gains, e.g. IAM CER 4.22%→3.92% with 9 lines.

### Cited Findings
- **Population/domain fine-tuning.** TrOCR on handwritten number cells: n=500 → 95%; n=5k → 97.17%; n=7k plus 3k cheque digits → 98.69% exact match. Cheque digits alone → 4.90%. — [Bhaskar et al. 2025](https://arxiv.org/pdf/2505.24676)
- **Writer adaptation by fine-tuning (Kohút & Hradiš, ICDAR 2023).** CTC line recognisers, CzechHWR data: 406k lines from about 4.5k writers; 19 target writers.
  - Abstract: "average relative CER improvement of 25% for 16 text lines and 50% for 256 text lines."
  - Full text, writer-independent: "even a single adaption text line without augmentations improved transcription accuracy by 5% on average"; "the improvements for 2–8 text lines were 10% to 20% on average"; "20% to 45% relatively, for 16–256 adaptation lines."
  - Writer-dependent baseline: 6% CER reduction without augmentation, 15% with augmentation.
  - Fine-tuning was "surprisingly resistant to overfitting."

  — [Kohút & Hradiš, arXiv 2302.06308](https://arxiv.org/html/2302.06308)
- **Writer adaptation by in-context learning (Simon et al., Jan 2026).** An 8M-parameter model conditions on labelled lines from the target writer. IAM CER: 4.22% (0 lines), 4.20% (1), 4.00% (3), 3.96% (5), 3.92% (9). RIMES CER: 2.91% (0) → 2.34% (9). That matches the gradient-based DocTTT (2.33%) with no parameter updates. — [Simon et al., arXiv 2603.29450](https://arxiv.org/html/2603.29450)
- **Children-specific adaptation.** E-TrOCR used IAM pre-training followed by fine-tuning on more than 1,800 child text lines. The size of the gain was not verifiable. — [Springer 2025](https://link.springer.com/chapter/10.1007/978-3-032-04614-7_7)
- **Multi-writer VLM baseline without adaptation.** Gemini 3.1 Flash-Lite reached 97.6% on single letters with no fine-tuning (Grabowski 2026), which shows a strong zero-shot floor for single-character answers. — [Grabowski 2026](https://arxiv.org/pdf/2606.11477)

### Inferences
- For this engine: first build a population set of a few thousand labelled answer crops from the school's own scans, ideally balanced by grade. The Bhaskar curve suggests 500 gets you to about 95% and about 5k to about 97%. Teacher corrections from the review queue can feed this set.
- Per-child profiles are probably low value at this stage. The published gains are relative CER cuts of 5-20% from a handful of samples. A child writes only a few dozen numbers per worksheet, and children's handwriting changes quickly between Grade 2 and 4. A profile could help as a tie-breaker, e.g. "this child writes 7 with a crossbar." That is an inference with no direct evidence.

### Gaps
- No study of per-child adaptation on young children's digits was found.
- No curve of exact-match accuracy against number of in-domain samples specifically for children's digits was found.

## 6. Tick / cross / checkbox (OMR-like) mark detection accuracy

### Takeaway
Classic, template-aligned mark detection on a known form is highly reliable: about 0.5 errors per 1,000 checkbox fields in automated forms processing. Unconstrained VLM reading of checkboxes is not: the best model scored 83.2 ANLS vs 97.5 for humans on CheckboxQA. VLMs also hallucinate ticks from layout alone.

### Cited Findings
- **Automated forms processing of checkboxes (older, 2012).** 0.46 errors per 1,000 fields, equal to double-key manual entry and better than single-key (3.70/1,000), across 21,608 checkbox fields. — [Paulsen et al., PLoS ONE 2012](https://pmc.ncbi.nlm.nih.gov/articles/PMC3320865/)
- **CheckboxQA (Turski et al., arXiv 2504.10419, 2025).** About 600 QA pairs on real documents. Best model Qwen2.5-VL-72B scored 83.2% ANLS; GPT-4o 66.7%; Gemini 2.0 Pro 59.7%; Pixtral-12B 56.9%; human 97.5%. — [arXiv 2504.10419](https://arxiv.org/abs/2504.10419)
- **VLMs inferring ticks that aren't there.** On handwritten medical forms, the most-hallucinated fields stemmed from "systematic misinterpretation of the checkbox structure, where models incorrectly infers a selected option despite the absence of a clear mark, effectively treating the visual layout itself as a signal." — [Pather et al. 2026](https://arxiv.org/pdf/2604.16504)
- **SurveyNet CNN on real survey sheets (Quiñones et al., 2026).** The data is 135 forms and 2,860 mark crops. Accuracy: Likert scale marks 89.8%; marks overlaid on text 84.0%; binary marks 97.0% (gender) and 82.0% (Yes/No). Digit entry (1-5) was only 50.0%. Baselines: OMRNet 77-80%; threshold-based OMR 70-74%. Failure modes: "faint or partial marks," noise, stroke thickness. — [SurveyNet, PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC13117292/)
- **Crossed-out answers.** VLMs recovered cells containing a crossed-out scribble plus a valid letter, where the YOLO detector "returns nothing." — [Grabowski 2026](https://arxiv.org/pdf/2606.11477)

### Inferences
- For ticks, crosses and "<"/">" symbols inside known boxes on a known template, simple ink-density or classifier approaches are the proven route. A VLM question-answering approach is weaker and prone to layout hallucination. For "which of these was ticked", measure ink per option box, and escalate only multi-mark or crossed-out cases to a VLM or a teacher.
- Faint pencil is the named failure mode in both OMR and HTR studies. Contrast normalisation before thresholding matters more than model choice.

### Gaps
- No published accuracy was found for mark detection on children's pencil ticks, or for handwritten comparison symbols ("<", ">", "=") in isolation.
- The SurveyNet dataset is small (135 forms), and its digit results (50%) look anomalous; treat it as weak evidence.
