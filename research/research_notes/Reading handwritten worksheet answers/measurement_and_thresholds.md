# Measuring accuracy and choosing what to auto-accept: evaluation and QC practice for automated reading and marking of handwritten answers

Scope note: these notes cover evaluation metrics, sample-size arithmetic, calibration, auto-accept thresholds, human-in-the-loop routing, multi-reader agreement, using teacher marks as validation, and rollout gates. The engine they apply to reads children's handwritten maths answers. Today it has 83 hand-verified answers. Its targets are at least 97% exact reading and at most 1% "silently wrong" answers. Answers below 70% OCR confidence go to a teacher, which is about 26% of them. There is a proposed gate of at least 95% agreement with teacher marking on closed items.

Dated sources are flagged inline with [DATED]. Some figures come only from search-result summaries and were not verified against the full text. These are flagged [SNIPPET-ONLY].

---

## 1. Which metrics are used in production, and what standards apply (educational measurement + forms processing)?

### Takeaway
Educational measurement judges an automated scorer against human raters on four things:
- Absolute agreement: quadratic weighted kappa (QWK) ≥ 0.70.
- Relative agreement: the machine's agreement with humans may fall at most 0.10 below human–human agreement.
- Score bias: standardized mean difference (SMD) within ±0.15, and within ±0.10 for each subgroup.
- Exact agreement: human–machine exact agreement may trail human–human exact agreement by at most about 5 points.

These come from Williamson, Xi & Breyer (2012), as codified by ACT (2021). Forms-processing and census practice instead uses field-level accuracy against a pre-set goal, measured independently. For right/wrong items with skewed prevalence, raw percent agreement and kappa can both mislead, so both need reporting, along with per-class error rates.

### Cited Findings
**Educational measurement thresholds (automated scoring vs humans)**
- ACT's 2021 technical brief tabulates the thresholds used for operational automated scoring (AS). All are "considered appropriate for operational use":
  - SMD between human and AS: −0.15 ≤ SMD ≤ 0.15 (Williamson, Xi & Breyer 2012).
  - SD ratio: 2/3 ≤ SD_human/SD_AS ≤ 1.50 (Wang & von Davier 2014).
  - Exact-agreement difference: EA_human,human − EA_human,AS ≤ 5.125% (McGraw-Hill CTB 2014; Pearson & ETS 2014).
  - QWK_human,AS ≥ 0.70 (Williamson et al. 2012).
  - QWK_human,human − QWK_human,AS ≤ 0.10 (Williamson et al. 2012).

  — [ACT Research Technical Brief, Wood, Yao, Haisfield & Lottridge, July 2021, "Establishing Standards of Best Practice in Automated Scoring", Table 2](https://www.act.org/content/dam/act/unsecured/documents/R2100-auto-scoring-standards-2021-07.pdf)
- Williamson et al. (2012) also require:
  - Pearson correlation with human scores of at least 0.70.
  - Engine–human agreement no more than 0.1 below human–human (H1–H2) agreement, "to ensure that .70 QWK doesn't allow a pass" for an engine that is worse than humans.
  - A defined "threshold for human adjudication" and rules for human intervention (response characteristics that make AS inappropriate).

  — [ACT 2021, Table 3, summarizing Williamson, Xi & Breyer 2012 p. 7](https://www.act.org/content/dam/act/unsecured/documents/R2100-auto-scoring-standards-2021-07.pdf); original: [Williamson, Xi & Breyer 2012, Educational Measurement: Issues and Practice 31(1):2–13](https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1745-3992.2011.00223.x) [DATED 2012, still the reference standard cited in 2021]
- Williamson et al. note that "if the inter-rater agreement of independent human raters is low, especially below the .70 threshold, then automated scoring is disadvantaged". In other words, the human gold standard has to be reliable first. — [ACT 2021 quoting Williamson et al. 2012 p. 7](https://www.act.org/content/dam/act/unsecured/documents/R2100-auto-scoring-standards-2021-07.pdf)
- Subgroup fairness thresholds:
  - Williamson et al. flag the population SMD above |0.15| and a subgroup SMD above |0.10|.
  - McGraw-Hill CTB tightened its population flag to |0.12|, because a large population SMD makes subgroup flags more likely.

  — [ACT 2021, Table 8, quoting McGraw-Hill Education CTB 2014 p. 15](https://www.act.org/content/dam/act/unsecured/documents/R2100-auto-scoring-standards-2021-07.pdf)
- QWK can hide errors. CTB found "an engine's quadratic weighted kappa (QWK) may be high even though the engine exact agreement rate in comparison is low" when the engine gives adjacent scores. CTB therefore also watches for a drop of more than 0.05 in perfect-agreement rate between human–human and engine–human scores. — [ACT 2021 quoting McGraw-Hill CTB 2014 p. 15](https://www.act.org/content/dam/act/unsecured/documents/R2100-auto-scoring-standards-2021-07.pdf)
- CCSSO & ATP (2013) say that when AI engines are used in place of human scoring, "or for confirmation or quality control of human scoring", they "should meet the same standards for accuracy and reliability that exist for human scoring of the same item type". — [ACT 2021 quoting CCSSO & ATP 2013 p. 131](https://www.act.org/content/dam/act/unsecured/documents/R2100-auto-scoring-standards-2021-07.pdf)
- AERA/APA/NCME Standards (2014):
  - Standard 2.7: where judgment enters scoring, report interrater consistency.
  - Standard 2.8: "When constructed-response tests are scored locally, reliability/precision data should be gathered and reported for the local scoring when adequate-size samples are available."

  — [ACT 2021 quoting AERA, APA & NCME 2014 p. 44](https://www.act.org/content/dam/act/unsecured/documents/R2100-auto-scoring-standards-2021-07.pdf)
- Non-attempts (blank, gibberish, refusals) are separated from valid attempts and handled in a different workflow using "condition codes". They are not scored by the main model. — [ACT 2021, Standard 7](https://www.act.org/content/dam/act/unsecured/documents/R2100-auto-scoring-standards-2021-07.pdf)

**Operational engine-vs-human numbers**
- Smarter Balanced FAQ: engine exact agreement with professional scorers was 81/82/83% on three items, against human–human agreement of 79/73/76%. On writing traits it was 76–82% against 65–72%. The FAQ also says: "Humans tend to agree with one another 60–75% of the time on scores and 80–95% of the time on condition codes." — [Smarter Balanced Interim Automated Scoring FAQ (undated)](https://smarterbalanced.alohahsap.org/content/contentresources/en/Smarter_Interim_Automated_Scoring_FAQ.pdf)

**Forms-processing and census accuracy measurement**
- Census 2000 (DCS 2000, more than 120 million forms, captured by OMR/OCR plus key-from-image):
  - OCR accuracy was "about 99.3 percent at each DCC, exceeding the 98-percent accuracy goal".
  - Key-from-image (KFI) accuracy was "97.6 percent or more at each DCC, exceeding the bureau's 96.5 accuracy goal".
  - In the Baltimore operational test, OCR accuracy was 99.7% and keying 98%, "validated by an independent organization" (RIT Research Corporation).

  — [GAO-AIMD-00-324R, 29 Sep 2000](https://www.govinfo.gov/content/pkg/GAOREPORTS-AIMD-00-324R/html/GAOREPORTS-AIMD-00-324R.htm) [DATED 2000]. A search summary gave slightly different figures (OCR over 99.36%, KFI 97.37% or more), probably from a later or different report. I did not verify which is final. — [search result: GAO/NAP Census 2000 reports](https://www.nationalacademies.org/read/10907/chapter/19)
- Vendor and industry claim: real-world ICR (handwriting) "typically sits between 85–95%", and reaches 97–99% on "structured, clearly hand-printed forms". — [Parseur blog (vendor, low evidentiary weight)](https://parseur.com/blog/intelligent-character-recognition) [SNIPPET-ONLY]
- Azure Document Intelligence:
  - Field confidence is described as "an estimated probability between 0 and 1 that the prediction is correct… a confidence value of 0.95 (95%) indicates that the prediction is likely correct 19 out of 20 times". It "can be used to determine whether to automatically accept the prediction or flag it for human review."
  - For custom models, "target a score of 80% or higher. For more sensitive cases, like financial or medical records, we recommend a score of close to 100%."
  - The read (OCR) confidence and the field-extraction confidence are separate, and both must be checked.

  — [Microsoft Learn, "Interpret and improve model accuracy and confidence scores" (updated 2026)](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/concept/accuracy-confidence)

**Prevalence effects on kappa**
- The "kappa paradox": the more imbalanced the category marginals, the higher the chance agreement, so kappa falls sharply even when observed agreement is high (Feinstein & Cicchetti 1990). — [J Clin Epidemiol 43:543–549](https://www.sciencedirect.com/science/article/abs/pii/089543569090158L) [DATED 1990, statistical property still holds]
- Worked example from pathology: 88% observed agreement gave Cohen's kappa of 0.43 but Gwet's AC1 of 0.85. The authors recommend reporting kappa together with percent agreement and a paradox-resistant measure such as AC1. — [PubMed 38283651](https://pubmed.ncbi.nlm.nih.gov/38283651/)

### Inferences
- For a closed right/wrong item there are only two categories. QWK then reduces to ordinary Cohen's kappa, since the weighting has no effect, so the 0.70 QWK / 0.10-degradation rule can be applied as kappa on tick/cross.
- The engine has two separate jobs, and each needs its own metric:
  - Reading: exact-match on the transcribed answer string, after normalising whitespace and equivalent forms. For short numeric answers, exact-match accuracy is the operational metric. Character error rate is diagnostic only, because a single wrong digit makes the answer wrong.
  - Marking: agreement on correct/incorrect with the teacher, reported as percent agreement, kappa or AC1, sensitivity on crosses and sensitivity on ticks.
- Worked illustration of why "≥95% agreement" alone is weak. Suppose 10% of answers are wrong and every disagreement is a missed cross.
  - The engine then says "correct" for 95% of answers, so agreement is 95%.
  - Chance agreement: p_e = 0.9×0.95 + 0.1×0.05 = 0.86. Kappa = (0.95 − 0.86)/0.14 ≈ 0.64, which fails the 0.70 bar.
  - Half of all wrong answers would be marked right.
  - The gate therefore needs a separate floor on "teacher-cross detected", i.e. recall on wrong answers.
- The ACT/CTB relative rule ("no worse than human–human by >5 points exact agreement / >0.10 kappa") needs a teacher–teacher baseline measured on the same items. Without one, the 95% gate has no reference point.
- "Silently wrong" is the forms-processing false-accept rate. Two denominators are possible:
  - Errors among auto-accepted items. This is the conditional risk that selective-prediction methods control.
  - Errors among all items. This equals the accepted-item risk × coverage.
  - With about 74% coverage, 1% of accepted items is about 0.74% of all items. The spec should state which denominator it means.

### Gaps
- I found no vendor-independent benchmark for "straight-through processing" (STP) rates in handwriting ICR. STP figures in vendor marketing are unverifiable.
- I found no published accuracy standard specific to *short numeric* constructed responses. The Williamson thresholds were developed for essays and short text, but ACT/CCSSO apply them to AS generally.

---

## 2. How big must a labelled evaluation set be to claim 97% or 99% accuracy, and how should it be stratified?

### Takeaway
With 83 answers you cannot demonstrate 97% accuracy even if all 83 are correct: the 95% lower bound is about 95.6%. To demonstrate a "silently wrong" rate of 1% or less with zero observed errors, you need about 300 accepted items (rule of three). Each error you allow raises that by roughly 150–175 items. The founder's "300+ gold answers" matches the zero-error case exactly, but it applies *per claim and per stratum*, and it counts *accepted* items.

### Cited Findings
- Rule of three: if zero events are seen in n trials, the 95% upper bound on the event rate is about 3/n. The standard example: if 300 parachutes all open, you can conclude with 95% confidence that fewer than 1 in 100 will fail. — [Hanley & Lippman-Hand 1983, JAMA 249:1743–1745](https://jamanetwork.com/journals/jama/fullarticle/385438) [DATED 1983, still standard]; [Rule of three (Wikipedia)](https://en.wikipedia.org/wiki/Rule_of_three_(statistics))
- Performance on small, single-exam datasets "fluctuates more… it is indeed commonly lower or larger than on a large dataset". The authors therefore propose a per-exam validation mechanism that uses the teacher's grading of the difficult items that were deferred to humans. — [Schneider, Richner & Riser 2022, "Towards Trustworthy AutoGrading of Short, Multi-lingual, Multi-type Answers", IJAIED](https://arxiv.org/pdf/2201.03425)
- Seed (gold) items must be representative. "It would be very easy to artificially improve the metrics by only including 'easy' seeds". Over-representing hard seeds does the opposite and under-estimates consistency. — [Ofqual, Marking consistency metrics: an update (2018, summer 2017 data)](https://assets.publishing.service.gov.uk/media/5bfbfd70e5274a0fb775cca3/Marking_consistency_metrics_-_an_update_-_FINAL64492.pdf)
- Validation "should include a range of score points, types and styles of writing, and other relevant considerations". — [ACT 2021 quoting CCSSO & ATP 2013 p. 131](https://www.act.org/content/dam/act/unsecured/documents/R2100-auto-scoring-standards-2021-07.pdf)
- Evaluation should be done at the task (item) level first, then aggregated to task type and reported score. — [ACT 2021 quoting Williamson et al. 2012 p. 8](https://www.act.org/content/dam/act/unsecured/documents/R2100-auto-scoring-standards-2021-07.pdf)
- Include every input variation, "for example, digital versus scanned PDFs", with "at least five samples of each type" for training. Visually distinct document types should be split into separate models. — [Microsoft Learn, Document Intelligence accuracy & confidence](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/concept/accuracy-confidence)

**Sample-size arithmetic (computed for these notes)**

Method: exact binomial (Clopper–Pearson via beta quantiles) and the Wilson score interval, computed with scipy. The figures are reproducible and are arithmetic, not literature claims.

- **The current 83-item gold set.** Two-sided 95% intervals by number of errors:

  | Errors | Observed accuracy | Wilson 95% interval | Clopper–Pearson lower bound |
  |---|---|---|---|
  | 0 | 100% | 95.6%–100% | 95.65% |
  | 1 | 98.8% | 93.5%–99.8% | — |
  | 2 | 97.6% | 91.6%–99.3% | — |
  | 3 | 96.4% | 89.9%–98.8% | — |

  Conclusion: 83 items cannot certify ≥97%, and cannot certify anything about a 1% silent-error rate.
- **Zero-error sample size** so that the one-sided 95% upper bound on the error rate is at or below the target (exact n = ln 0.05 / ln(1−p)):

  | Target error rate | n (exact) | n (rule of three) |
  |---|---|---|
  | 3% | 99 | 100 |
  | 1% | 299 | 300 |
  | 0.5% | 598 | 600 |
  | 0.1% | 2,995 | 3,000 |

- **Allowing k observed errors**, the minimum n for a one-sided 95% Clopper–Pearson upper bound at or below the target:

  | Observed errors k | n for error ≤ 1% | n for error ≤ 3% |
  |---|---|---|
  | 0 | 299 | 99 |
  | 1 | 473 | 157 |
  | 2 | 628 | 208 |
  | 3 | 773 | 257 |
  | 5 | 1,049 | 348 |

- **Planning for power** (normal approximation, one-sided α = 0.05, 80% power):
  - Showing reading accuracy ≥97% needs about 652 items if the true accuracy is 98.5%, and about 332 if it is 99%.
  - Showing a silent-error rate ≤1% needs about 1,990 items if the true rate is 0.5%, and about 753 if it is 0.25%.
- **Teacher-agreement gate of ≥95%**, as Wilson lower bounds:

  | Observed agreement | n | Wilson lower bound |
  |---|---|---|
  | 97% | 300 | 94.4% (fails) |
  | 97% | 500 | 95.1% (passes) |
  | 98% | 200 | 94.97% (borderline) |
  | 98% | 300 | 95.7% (passes) |

- **Precision at 97% observed accuracy** (Wilson half-width):

  | n | Approximate interval |
  |---|---|
  | 83 | ±4 points |
  | 300 | 94.4–98.4% |
  | 1,000 | 95.8–97.9% |
  | 2,000 | 96.2–97.7% |

### Inferences
- The 1% silent-wrong claim is about *auto-accepted* items, so the ~300 must be accepted gold items. At about 74% coverage that means roughly 400+ total gold answers, and more if any error appears (473 accepted items with one error, about 640 total).
- Stratify by capture mode (scanner vs phone photo), grade/age band, answer type (single digit, multi-digit, fraction/decimal, units, word answer) and blank/non-attempt. Report each stratum separately, because an aggregate can pass while one stratum fails. Only strata that must individually carry the ≤1% claim need about 300 accepted items each. Others can be pooled, with the stratum shown as a diagnostic.
- Gold labels are "definitive" readings. Double-key them: two independent humans transcribe, and any mismatch is adjudicated (see section 4 on the double-entry evidence). Otherwise gold-label error of 0.5–6% (see section 6) sets a noise floor comparable to the 1% target.
- A pragmatic sequence is to continuously add teacher-verified items and publish a Wilson/Clopper–Pearson bound on each dashboard metric instead of a point estimate. The gate then trips on the *lower bound*, not the observed rate.

### Gaps
- No source I found prescribes a stratification scheme specific to handwritten numeric answers. The strata above are inferred from the general guidance (ACT/CCSSO: "range of score points, types and styles"; Microsoft: "digital versus scanned").

---

## 3. Confidence calibration and auto-accept thresholds that guarantee a target error rate

### Takeaway
Raw OCR and model confidence is usually not a calibrated probability, so a fixed "70% confidence" cut guarantees nothing by itself. Current practice is to pick the threshold empirically on a held-out, labelled calibration set, so that the *upper confidence bound* of error among accepted items stays below the target. Formal methods for this exist: Geifman & El-Yaniv's selective classification with guaranteed risk, and Learn-then-Test / conformal risk control.

### Cited Findings
- **Selective classification with guaranteed risk (SGR).**
  - Given a trained classifier and a user-set desired risk, SGR finds a rejection rule that meets that risk "with high probability".
  - Reported result: "2% error in top-5 ImageNet classification… with probability 99.9%, and almost 60% test coverage."

  — [Geifman & El-Yaniv 2017, "Selective Classification for Deep Neural Networks", NeurIPS, arXiv:1705.08500](https://arxiv.org/abs/1705.08500)
- **Learn then Test (LTT).**
  - Calibrates any pretrained model so that its predictions satisfy explicit, finite-sample risk guarantees, without refitting the model.
  - It reframes risk control as multiple hypothesis testing: each candidate threshold is tested with an upper confidence bound (e.g. Hoeffding), with a family-wise correction (e.g. Bonferroni).
  - Selective classification, meaning abstention on the hardest examples, is cited as a key application.

  — [Angelopoulos, Bates, Candès, Jordan & Lei, "Learn then Test", Annals of Applied Statistics 2025, arXiv:2110.01052](https://arxiv.org/html/2110.01052v5)
- Newer variants:
  - Selective Conformal Risk Control abstains on low-confidence inputs and applies conformal risk control to the accepted subset. — [Xu, Guo & Wei, arXiv:2512.12844](https://arxiv.org/html/2512.12844v2)
  - False-selection-rate control for selective classification. — [arXiv:2311.03811](https://arxiv.org/pdf/2311.03811)
  - One paper audits bound tightness and flags "false sense of safety" when exchangeability (i.e. calibration data like live data) fails. — [arXiv:2606.15153](https://arxiv.org/pdf/2606.15153) [title only; not read]
- **Temperature scaling** learns one parameter that softens logits. It improves the confidence estimates but does not change the predicted class. With uncalibrated uncertainty "few uncertain predictions are rejected at first", whereas calibrated uncertainty gives "an almost linear relationship", which allows robust rejection. — [arXiv:1909.13550, "Well-calibrated Model Uncertainty with Temperature Scaling for Dropout Variational Inference"](https://arxiv.org/pdf/1909.13550). The canonical reference showing that modern networks are over-confident, and introducing reliability diagrams, expected calibration error (ECE) and temperature scaling, is [Guo et al. 2017, "On Calibration of Modern Neural Networks", arXiv:1706.04599](https://arxiv.org/abs/1706.04599) [not re-fetched in this session].
- **OCR/HTR confidence in practice:**
  - A 2026 industrial HTR case study reports "substantial overlap between distributions of confident and erroneous readings", which "prevents the confidence metric from serving as a reliable indicator for automated decision-making". — [IJIDeM 2026, "Evaluating the suitability of handwritten text recognition for industrial operations… acceptance sampling inspection workflow"](https://link.springer.com/article/10.1007/s12008-026-02513-9) [SNIPPET-ONLY, paywalled]
  - Another study found a correlation between HTR confidence and errors of r = −0.738 once outliers were excluded ("moderate but significant"). — [ResearchGate: "How Scalable is Quality Assessment of Text Recognition? A Combination of Ground Truth and Confidence Scores"](https://www.researchgate.net/publication/397841453_How_Scalable_is_Quality_Assessment_of_Text_Recognition_A_Combination_of_Ground_Truth_and_Confidence_Scores) [SNIPPET-ONLY]
- **LLM grading of handwritten maths with a confidence filter.** GPT-4 graded a German university mock maths exam (54 consenting students, 6 questions, 21 points).
  - Overall accuracy was 0.59–0.62, with Krippendorff's α of 0.22–0.44. The authors treat α ≥ 0.8 as reliable and α < 2/3 as unacceptable.
  - A sampling-based "Can Decide" confidence condition was met by about 83% of responses. Among those, the false-positive rate, i.e. confident-but-wrong, was 7–41% per problem, averaging 0.27: "in about a quarter of the grading instances, the algorithm indicated confidence into a grading result that did not correspond to the ground truth."

  — [arXiv:2408.11728 (2024), "AI-assisted Automated Short Answer Grading of Handwritten University Level Mathematics Exams", arXiv:2408.11728](https://arxiv.org/html/2408.11728v1)
- A separate study of GPT-4o grading handwritten college maths found that rubrics improve alignment, but "overall accuracy is still too low for real-world settings". — [arXiv:2411.05231, "Evaluating GPT-4 at Grading Handwritten Solutions in Math Exams" (2024)](https://arxiv.org/html/2411.05231v1) [SNIPPET-ONLY]
- **Asymmetric error targets reduce coverage sharply.**
  - Autograding short text and numeric answers from about 10 million question–answer pairs gave about 85–90% correct right/wrong decisions if everything was auto-graded. The authors call this "clearly below human performance".
  - They use two thresholds: auto-mark correct above T_c, auto-mark incorrect below T_i, and defer to a human in between. The teacher sets the accuracy constraints.
  - With a target of 2% false positives (wrong answer marked right) and 0% false negatives ("does not fail any student unjustly"), only "about 10% of all questions are graded" automatically.

  — [Schneider, Richner & Riser 2022, IJAIED, arXiv:2201.03425](https://arxiv.org/pdf/2201.03425)
- **Operational threshold-setting in assessment.** Smarter Balanced's engine flags a response as low-confidence when its confidence value "is in the bottom 15% of all confidence values in a validation sample". In operational summative testing these go to human scorers. "The thresholds for the confidence value are set in consultation with the state and based upon a review of the data." — [Smarter Balanced Automated Scoring FAQ (undated)](https://smarterbalanced.alohahsap.org/content/contentresources/en/Smarter_Interim_Automated_Scoring_FAQ.pdf)
- **Forms processing.** Microsoft advises checking both OCR ("read") confidence and field confidence, and combining them into "a composite confidence score for the field". — [Microsoft Learn](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/concept/accuracy-confidence)

### Inferences
- The current rule, raw OCR confidence < 0.70 goes to a teacher, is a *coverage* choice (about 74% auto-accepted), not a *risk* guarantee. The auditable replacement is a risk-coverage procedure:
  1. On a held-out labelled calibration set, sort candidate thresholds t from strict to lenient.
  2. For each t, compute the accepted count n_t and the silent errors k_t among the accepted items.
  3. Compute the one-sided 95% Clopper–Pearson upper bound.
  4. Choose the most lenient t whose bound is ≤ 1%. Testing thresholds in fixed sequence from strict to lenient, and stopping at the first failure, is the LTT-style fixed-sequence procedure, which needs no Bonferroni penalty.
  5. Report coverage at that t as the straight-through rate.
- With 83 labels this procedure returns "no threshold certifies 1%". That is a correct answer, not a bug.
- The engine's confidence signal can be a composite: OCR confidence, plus second-reader agreement (section 4), plus a format check (e.g. the parsed value is a valid number of the expected type or range). The threshold is then set on that composite by the same procedure. Calibration methods such as temperature scaling or isotonic regression make the scores interpretable, but the risk-coverage selection is what gives the guarantee.
- Conformal and LTT guarantees assume calibration data exchangeable with live data. A new capture mode, such as phone photos, or a new grade breaks this, so the threshold must be recalibrated per stratum or re-validated after drift.
- Asymmetric costs matter for marking. Marking a wrong answer "right" (a hidden learning gap) and marking a right answer "wrong" (an unfair cross) may warrant different ceilings. Schneider et al. show that a strict ceiling on one side can drop coverage from about 90% to about 10%.

### Gaps
- I found no published reliability diagram or ECE figure for Google Vision, Textract or Azure *handwriting* confidence on children's digits. Calibration of those specific engines has to be measured locally.

---

## 4. Agreement between two independent readers as a confidence signal (voting OCR, double-keying, census KFI)

### Takeaway
Combining independent readers reliably cuts errors. Voting across OCR passes or engines removes 20–50% or more of errors, and double data entry is far more accurate than a single keyer with visual checking. Agreement between two readers is therefore a strong auto-accept signal, and disagreement is a natural routing trigger. This only holds when the readers' errors are reasonably independent.

### Cited Findings
- **Consensus voting across OCR passes.** "Between 20 and 50% of the errors caused by a single OCR package can be eliminated by simply scanning a page three times and running a 'consensus sequence' voting procedure." — [Lopresti & Zhou 1997, "Using Consensus Sequence Voting to Correct OCR Errors", Computer Vision and Image Understanding](https://www.sciencedirect.com/science/article/abs/pii/S1077314296905020) [DATED 1997]
- **Multi-engine combination.** Search summaries report the following. I could not tie each number to a specific paper, and none were verified against full text.
  - A 69.1% relative reduction in word error rate versus the average of five engines.
  - A 24.6% relative gain over the best single engine of five, on WWII typewritten documents, using voting plus dictionary features.
  - Greater than 4-fold error reductions from multi-engine pipelines with alignment borrowed from molecular systematics, on herbarium labels.

  — [Applications in Plant Sciences 2023 (NSF PAR)](https://par.nsf.gov/servlets/purl/10566017); [LV-ROVER, arXiv:1707.07432](https://arxiv.org/pdf/1707.07432); [Reul et al., cross-fold training and voting, arXiv:1711.09670](https://arxiv.org/pdf/1711.09670) [SNIPPET-ONLY attribution]
- **Double entry vs visual checking.** 195 undergraduates were randomly assigned to a method and each entered 30 data sheets.
  - Visual checking produced 2,958% more errors than double entry, and was not significantly better than single entry.
  - 66% of visual-checking participants produced a wrong coefficient alpha.
  - Double entry took 33% longer than visual checking.

  — [Barchard & Pace 2011, Computers in Human Behavior 27(5)](https://www.sciencedirect.com/science/article/abs/pii/S0747563211000707) [DATED 2011]
- Follow-up work: double entry "locates and corrects more data-entry errors than does visual checking or reading the data out loud with a partner". — [Behavior Research Methods (2019/2020), "Comparing the accuracy and speed of four data-checking methods"](https://link.springer.com/article/10.3758/s13428-019-01207-3)
- **Machine-as-second-reader in high-stakes assessment (ETS GRE "check score").**
  - The first human score stands alone if the unrounded e-rater score is within ±0.5 of it.
  - Otherwise a second human scores the essay and the two human scores are averaged. A third human is added if they differ by more than a point.
  - "the e-rater score does not contribute to the analytical writing score." The ±0.5 threshold was validated in earlier GRE research (Ramineni et al. 2012).

  — [Breyer et al. 2014, "A Study of the Use of the e-rater Scoring Engine for the Analytical Writing Measure of the GRE revised General Test", ETS RR](https://files.eric.ed.gov/fulltext/EJ1109327.pdf); [Wiley version](https://onlinelibrary.wiley.com/doi/full/10.1002/ets2.12022)
- **The implementation continuum.** Williamson et al. order implementations "from more conservative to more liberal":
  - Automated quality control of human scoring (the discrepancy threshold sends the response to a second human; the reported score is human-only).
  - Automated plus human scores averaged, with adjudication on discrepancy.
  - "Reporting scores solely from the automated system. This is the most liberal use."
  - High-stakes use carries "a higher burden of both the amount and quality of evidence".

  — [ACT 2021, Table 6, quoting Williamson et al. 2012 p. 5](https://www.act.org/content/dam/act/unsecured/documents/R2100-auto-scoring-standards-2021-07.pdf)
- **Census fallback.** In Census 2000, clerks keyed data items from images when automation could not read the responses. KFI accuracy was measured separately against its own goal of 96.5%, and achieved 97.6% or more. — [GAO-AIMD-00-324R, 2000](https://www.govinfo.gov/content/pkg/GAOREPORTS-AIMD-00-324R/html/GAOREPORTS-AIMD-00-324R.htm) [DATED]
- **Independence caveat from exam-board practice.** Mark-remark pairs are treated as statistically independent only when arrived at independently. Independence fails if the examiners who set a seed's definitive mark are later monitored on the same seed, or remember marks from feedback. — [Ofqual 2018](https://assets.publishing.service.gov.uk/media/5bfbfd70e5274a0fb775cca3/Marking_consistency_metrics_-_an_update_-_FINAL64492.pdf)

### Inferences
- A two-reader design fits the census, double-keying and e-rater check-score model. The design:
  - Reader A is, say, the current OCR; reader B is a different engine or a vision-LLM.
  - Accept automatically only when both readings match exactly *and* confidence is above threshold.
  - Send any mismatch to the teacher.
- Agreement is worth measuring as a routing signal: estimate P(wrong | both agree) on the gold set. It must still pass the section-3 risk bound, because correlated readers (e.g. two models that both read a child's "7" as "1") agree on the same wrong answer.
- LLM "self-consistency" style confidence (sampling the same model repeatedly) is *not* an independent second reader. The arXiv:2408.11728 result (about 27% false positives among "confident" grades, section 3) is a warning against treating it as one.

### Gaps
- I found no published study quantifying P(error | two engines agree) on handwritten *digits/short numeric answers* specifically. This conditional error rate has to be measured locally.

---

## 5. Human-in-the-loop routing practice (A2I, verification stations, exam-board QC, feedback)

### Takeaway
Mature systems do three things:
1. Route low-confidence and "unusual" items to humans.
2. Also send a *random sample of confidently-accepted items* to humans for monitoring.
3. Monitor the humans themselves with hidden gold items (seeds).

Typical shares are about 5% seeds (exam boards), 10% read-behind (MCAS), and 20–40% total human scoring (Smarter Balanced summative).

### Cited Findings
- **Amazon A2I with Textract.** Activation conditions can:
  - Start review for specific form keys based on confidence.
  - Start review when specific keys are missing.
  - Start review for all keys "with confidence scores in a specified range".
  - "Randomly send a sample of forms to humans for review".

  Two confidences are exposed: *identification* (the key–value pair was detected) and *qualification* (the text inside it). A2I "is no longer open to new customers" (existing customers continue; no new features planned). — [AWS SageMaker docs, "Use Amazon Augmented AI with Amazon Textract"](https://docs.aws.amazon.com/sagemaker/latest/dg/a2i-textract-task-type.html) [DATED: service closed to new customers as of fetched page]
- The threshold ranges are set between 0 and 99, and the random sample exists "for model-monitoring purposes". — [AWS Textract Developer Guide, A2I](https://docs.aws.amazon.com/textract/latest/dg/a2i-textract.html?icmpid=docs_a2i_lp) [SNIPPET-ONLY]
- **Smarter Balanced (operational summative).** "low-confidence responses and responses receiving certain condition codes are routed for professional human scoring. Additionally, as a monitoring step, a portion of all other responses also receives a human score. In practice, the portion of responses routed for human scoring ranges between 20% and 40%". For interim (classroom) use, "low-confidence responses are flagged for educators to review and score". — [Smarter Balanced Automated Scoring FAQ (undated)](https://smarterbalanced.alohahsap.org/content/contentresources/en/Smarter_Interim_Automated_Scoring_FAQ.pdf)
- **Massachusetts MCAS 2024.**
  - Grade 3–8 essays: automated scoring gives the first score, and "trained human scorers providing the read-behind score on 10% of responses".
  - Grade 10: all essays are scored twice.
  - Essays the engine cannot score go to humans.
  - DESE monitors both human and automated scoring.

  — [MA DESE, "2024 Scoring Student Answers to Constructed-Response Questions and Essays"](https://www.doe.mass.edu/mcas/student/2024/scoring.html)
- **Exam-board seeding (England).**
  - Pre-marked "seed" items with a senior-examiner "definitive mark" are inserted "at times and intervals unknown to the examiner (sampling rates of approximately 5% are typical)".
  - "If the mark is out of tolerance the examiner may be given guidance or retraining, or stopped from marking."
  - Some boards also use *blind sample double-marking*: either a "consensual" approach, where the higher of two marks stands unless they differ by more than a tolerance, or a "hierarchical" approach, where a senior examiner's mark stands.
  - The dataset held 16.4 million marking events (16.2 million from seeds, 198,000 double-marked) across 453 components, from the summer 2017 session.

  — [Ofqual, Marking consistency metrics: an update (2018)](https://assets.publishing.service.gov.uk/media/5bfbfd70e5274a0fb775cca3/Marking_consistency_metrics_-_an_update_-_FINAL64492.pdf)
- A 1-mark item "would likely have no tolerance, while an 8-mark item might have a tolerance of plus or minus 1 mark". — [search summary of Ofqual marking-consistency coverage](https://ofqual.blog.gov.uk/2018/04/20/exam-marking-how-technology-is-improving-the-quality-of-marking/) [SNIPPET-ONLY, source attribution unverified]
- **Choosing which responses humans see.** "Reward sampling" of responses for human scoring, versus random sampling, improved accuracy by 19.80% and QWK by 25.60% on average with only 30% of responses human-scored. Random sampling gave 8.6% and importance sampling 12.2%. The authors also give an algorithm to *estimate* accuracy and QWK with statistical guarantees from the sample. — [Kumar Singla, Krishna, Shah & Chen 2021, "Using Sampling to Estimate and Improve Performance of Automated Scoring Systems with Guarantees", arXiv:2111.08906](https://arxiv.org/abs/2111.08906)
- **Feeding corrections back.**
  - Microsoft: when accuracy is high but confidence low, "the model would benefit from retraining with at least five more labeled documents". Also: "Consider incorporating human review into your workflows." — [Microsoft Learn](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/concept/accuracy-confidence)
  - Schneider et al. reuse the teacher's grades on the difficult items deferred to them as a validation set per exam, to detect "strong deviations from expected accuracy". — [arXiv:2201.03425](https://arxiv.org/pdf/2201.03425)

### Inferences
- The engine's current queue (the 26% of answers below 0.70 confidence) is the "low-confidence route". Two things are missing:
  - A *random audit* of auto-accepted items. This is the only unbiased estimator of the live silent-wrong rate, because teacher-routed items are by construction the hard ones.
  - *Hidden gold* items, if teacher verification itself is to be trusted.
- Every teacher correction in the queue should be stored as a labelled example, tagged "routed" vs "audit". Audit labels estimate live error. Routed labels feed retraining and threshold recalibration, but must not be pooled into the accuracy estimate, because that would bias it.
- In classroom (interim) use, Smarter Balanced flags items for *educators* rather than paid scorers. This is the closest published analogue to a teacher-review queue.

### Gaps
- Google Document AI's human-review product status and parameters were not checked in this session.
- No source gave a recommended random-audit *rate* derived from a statistical argument. The 5%, 10% and 20–40% figures are practice, not derivations.

---

## 6. Using teachers' existing marks as validation: studies, handling teacher error, typical teacher–teacher agreement

### Takeaway
Teacher marks are a useful *reference* but not a *gold standard*.
- Exam-board data shows maths marking is the most consistent subject: 0.96 probability of the definitive qualification grade.
- Still, human error on repetitive grading runs at about 0.5–6%, and even "definitive" marks are sometimes wrong.
- Disagreements between engine and teacher should therefore go to adjudication, not be scored automatically as engine errors.

I found no published study comparing an automated reader against teachers' in-class ticks and crosses on primary worksheets.

### Cited Findings
- **Subject differences in marking consistency.**
  - The probability of receiving the "definitive" qualification grade ranges "from 0.96 (a mathematics qualification) to 0.52 (an English language and literature qualification)".
  - The probability of the definitive or adjacent grade is above 0.95 for all qualifications.
  - Ofqual's explanation: "Mathematics questions are generally low mark tariff questions with an objectively correct answer."
  - Comparison to a single definitive mark "represents a relatively stringent measure". If other legitimate marks were counted, the metrics "would be somewhat higher".

  — [Ofqual 2018 (summer 2017 data)](https://assets.publishing.service.gov.uk/media/5bfbfd70e5274a0fb775cca3/Marking_consistency_metrics_-_an_update_-_FINAL64492.pdf)
- At item level, examiners in physics were reportedly 95% likely to agree with the definitive mark per question, compared with 50% in English. — [Schools Week coverage of Ofqual 2016 marking consistency report](https://schoolsweek.co.uk/half-of-english-literature-exam-papers-not-given-correct-grade-ofqual-report-finds/); [Ofqual Nov 2016 report](https://assets.publishing.service.gov.uk/government/uploads/system/uploads/attachment_data/file/681625/Marking_consistency_metrics_-_November_2016.pdf) [SNIPPET-ONLY, press summary; DATED 2016]
- **The "definitive" mark can be wrong.** Where the most frequent examiner mark differs from the definitive mark, "there is a possibility that the definitive mark is wrong" (Bramley & Dhawan 2010). — [Ofqual 2018](https://assets.publishing.service.gov.uk/media/5bfbfd70e5274a0fb775cca3/Marking_consistency_metrics_-_an_update_-_FINAL64492.pdf)
- **Automarked objective items** (multiple choice, objective response) were excluded from the mark-remark data and "assum[ed]… marked perfectly accurately". — [Ofqual 2018](https://assets.publishing.service.gov.uk/media/5bfbfd70e5274a0fb775cca3/Marking_consistency_metrics_-_an_update_-_FINAL64492.pdf)
- **Agreement on 6-mark items.** International literature reports exact agreement rates of 46–75% and adjacent (±1) agreement of 87–98%. England's rates fall within those bounds and were stable from 2013 to 2017. — [Ofqual 2018](https://assets.publishing.service.gov.uk/media/5bfbfd70e5274a0fb775cca3/Marking_consistency_metrics_-_an_update_-_FINAL64492.pdf)
- **Human error on repetitive grading.** "Humans make errors as well, and the risk is higher for repetitive tasks like grading the same question dozens of times. For such tasks, error rates have been reported to be in the range of 0.5% to 6%". This is a secondary citation, p. 412 of their reference [46]. — [Schneider, Richner & Riser 2022](https://arxiv.org/pdf/2201.03425)
- **Validating against teacher grades.** Schneider et al. validate the autograder per exam using the teacher's own grading of the difficult, human-delegated items. They show that "strong deviations from expected accuracy can be reliably detected". — [arXiv:2201.03425](https://arxiv.org/pdf/2201.03425)
- **Human–human agreement on condition codes and scores.** Humans agree "60–75% of the time on scores and 80–95% of the time on condition codes" (Smarter Balanced, mostly ELA and short text). — [Smarter Balanced FAQ](https://smarterbalanced.alohahsap.org/content/contentresources/en/Smarter_Interim_Automated_Scoring_FAQ.pdf)
- **Human scores constrain the machine.** "Automated scoring is largely dependent on the quality of human scores", and models "developed with data from low-quality human scoring will result in poor AS engine performance". — [ACT 2021, Standard 7](https://www.act.org/content/dam/act/unsecured/documents/R2100-auto-scoring-standards-2021-07.pdf)
- The arXiv:2408.11728 study (handwritten university maths, GPT-4) did not report a human–human baseline. — [arXiv:2408.11728](https://arxiv.org/html/2408.11728v1)

### Inferences
- Treat each engine–teacher disagreement as one of three things: (a) a reading error, (b) a marking-rule error, or (c) a teacher error. Adjudicate a sample of disagreements with a second adult who is blind to both marks. With teacher error at 0.5–6%, a 95% raw-agreement gate could fail purely because of teacher slips.
- Agreement against teacher ticks measures the *whole chain*: read the answer, then compare it to the key. It does not isolate reading accuracy. The reading metric (97% exact) still needs separately transcribed gold.
- Red-pen marks sit on the same page image, so there are two contamination risks:
  - The engine could read the teacher's tick as part of the answer, or could learn to key off ticks. To keep validation independent, use an image region or version that excludes teacher ink, or unmarked scans.
  - Teacher marks are not blind to the answer layout either, but that is normal.
- For simple 1-mark numeric items, exam practice allows no tolerance, and maths shows the highest human consistency. A teacher–teacher baseline measured locally, by double-marking about 200–300 items, is the reference for the ACT "no worse than human–human" rule. The literature does not supply one for primary worksheets.

### Gaps
- I found no published study that compares automated reading or marking with teachers' *own classroom* ticks and crosses on the same scripts, and no published teacher–teacher agreement rate for 1-mark numeric classroom items. Ofqual's item-level maths agreement figures were not extracted numerically in this session; only the grade-level 0.96 was verified.

---

## 7. Rollout practice: parallel running (shadow mode) and acceptance gates before switching off human marking

### Takeaway
High-stakes programmes move up a ladder, from automated QC of human marking, to machine plus human with adjudication, to machine-only with a human read-behind. At each rung they check the Williamson/ACT criteria against human–human baselines, fix accuracy goals *in advance*, and validate independently. Even at the most automated rung, a permanent human sample continues: 10% read-behind at MCAS, 20–40% at Smarter Balanced.

### Cited Findings
- **Implementation ladder,** from "more conservative to more liberal": automated QC of human scoring, then automated and human scores averaged with adjudication, then automated-only reporting, "the most liberal use". High-stakes use needs more and better evidence. — [ACT 2021 quoting Williamson et al. 2012 p. 5](https://www.act.org/content/dam/act/unsecured/documents/R2100-auto-scoring-standards-2021-07.pdf)
- "if CAS is viewed as the human scorer then CAS may have a different validity criteria then if viewed as a read-behind." — [ACT 2021 quoting Yang et al. 2002 p. 408](https://www.act.org/content/dam/act/unsecured/documents/R2100-auto-scoring-standards-2021-07.pdf) [DATED 2002]
- **GRE check-score deployment.** e-rater was deployed as a *check* on a single human. Discrepancies beyond ±0.5 trigger a second human, and the machine score never enters the reported score. — [Breyer et al. 2014, ETS](https://files.eric.ed.gov/fulltext/EJ1109327.pdf)
- **Engine approval criteria at Smarter Balanced.** Engines are approved by psychometricians and must show "the agreement of the engine with humans is similar to the agreement of two humans". Operationally, low-confidence items plus a monitoring sample stay human-scored (20–40% in total). — [Smarter Balanced FAQ (undated)](https://smarterbalanced.alohahsap.org/content/contentresources/en/Smarter_Interim_Automated_Scoring_FAQ.pdf)
- **MCAS steady state.** Machine first score plus 10% human read-behind for grades 3–8. Grade 10 remains fully double-scored. — [MA DESE 2024](https://www.doe.mass.edu/mcas/student/2024/scoring.html)
- **Census 2000 gates.** Accuracy goals were fixed before operations (OCR 98%, KFI 96.5%). The system was validated in an operational test by an independent organisation (RIT Research Corp.) and exceeded both goals (OCR 99.7%, keying 98%) before and during production. — [GAO-AIMD-00-324R, 2000](https://www.govinfo.gov/content/pkg/GAOREPORTS-AIMD-00-324R/html/GAOREPORTS-AIMD-00-324R.htm) [DATED]
- **Ongoing monitoring** is expected. Wang & von Davier (2014) describe e-rater monitoring; CTB watches for a drop of more than 0.05 in exact agreement; the Standards require monitoring procedures. — [ACT 2021](https://www.act.org/content/dam/act/unsecured/documents/R2100-auto-scoring-standards-2021-07.pdf)
- **Exam-board human markers** are continuously monitored with hidden seeds (about 5%), and are stopped if out of tolerance. This is the same discipline applied to people. — [Ofqual 2018](https://assets.publishing.service.gov.uk/media/5bfbfd70e5274a0fb775cca3/Marking_consistency_metrics_-_an_update_-_FINAL64492.pdf)
- **Per-exam validation.** Schneider et al. recommend validating per exam and not just in aggregate, because small-set performance "fluctuates more". — [arXiv:2201.03425](https://arxiv.org/pdf/2201.03425)

### Inferences
Mapped onto the school engine, the literature supports this gate sequence.

1. **Shadow.** Teachers keep marking. The engine marks the same scripts, and its verdict is hidden from the teacher to avoid anchoring. Measure, per item type and per capture mode:
   - Agreement, kappa or AC1, and recall on teacher crosses.
   - Wilson or Clopper–Pearson lower bounds on each.
   - Adjudication of disagreements to separate engine error from teacher error.
2. **Pass criteria, fixed in advance** as Census did, rather than chosen after seeing results:
   - (a) Lower 95% bound on engine–teacher agreement ≥ 95%. Observed 97% needs n ≈ 500; observed 98% needs n ≈ 300.
   - (b) Kappa ≥ 0.70, and no more than 0.10 below a locally measured teacher–teacher kappa.
   - (c) Recall on teacher-marked wrong answers above a floor, e.g. ≥ 95%, so skewed prevalence cannot hide missed crosses.
   - (d) Silent-wrong upper bound ≤ 1% on auto-accepted items: at least 299 accepted with 0 errors, or 473 with 1.
   - (e) Criteria met in every stratum that will run unattended.
3. **Check-score stage,** following ETS. The teacher still marks. The engine flags only disagreements, so it saves adjudication effort without replacing the teacher.
4. **Machine-first with read-behind,** following MCAS and Smarter Balanced. The engine marks; low-confidence and two-reader-disagreement items go to the teacher; plus a permanent random audit of about 5–10% of auto-accepted items to track live silent-wrong rate and drift, with automatic fallback to stage 3 if the audit bound crosses 1%.

Further points:
- The external spec's "≥95% agreement" is *below* the precedent bars. Census OCR aimed for 98%. Item-level agreement in exam maths is higher than the 0.96 grade-level figure. Raw agreement also inflates under skewed prevalence (section 1). Keeping 95% as the headline is fine only if criteria (b) and (c) sit beside it.
- An eval set of this kind is exactly what the user's global bar requires ("any model-generated output ships with an eval set"). The shadow period *is* that eval set, and it keeps growing.

### Gaps
- I found no published account of a school or edtech product switching off *teacher* marking of handwritten maths after a shadow period, and no named acceptance gate from such a rollout. The gates above are assembled from high-stakes assessment and census practice by analogy.
- Durations of parallel running (weeks or cycles) before cut-over were not found in the sources reviewed.
