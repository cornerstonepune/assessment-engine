# SchoolOS: Autonomous K-10 Learning Lifecycle Operating System
## Product Requirements & Lean Architecture Document (PRD / PAD)
**Version:** 1.0  
**Target:** Nursery to Grade 10 (N-10) Adaptive Education  
**Architecture Paradigm:** Event-Driven Orchestration with Off-The-Shelf Micro-Engines (Zero-Bespoke-Bloat)

---

## 1. Executive Strategy: The Anti-Bloat Philosophy

Building an end-to-end school operating system from scratch often leads to hundreds of thousands of lines of fragile, unmaintainable code. To prevent this, SchoolOS follows a strict **"Plumbing & Glue" Architecture**:
1. **Never write an ML pipeline from scratch** when mature open-source engines exist (e.g., OpenCV, Surya, Faster-Whisper, PyBKT).
2. **Never build custom workflow engines** when state machines with deterministic guarantees exist (e.g., Temporal / LangGraph).
3. **Never send high-volume baseline tasks to frontier models**; use a tiered, cost-optimized routing proxy (LiteLLM) with specialized, sub-cent vision and language models.
4. **Enforce Human-in-the-Loop (HITL) by Exception only**: If a human must approve every single item, the system stalls. Automation handles high-confidence events; humans intervene exclusively on ambiguities, edge cases, and safety checks.

---

## 2. End-to-End Workflow Specifications & HITL Gates

Below are the 5 operational engines of SchoolOS. Each workflow outlines inputs, internal sub-steps, exact outputs, and its **Human-in-the-Loop (HITL)** governance checkpoint across the Nursery-to-Grade-10 (N-10) spectrum.

```
+---------------------------------------------------------------------------------------+
|                                    1. CURRICULUM ENGINE                               |
| Skill Graph (NCERT/CBSE) ──> Pedagogy Agent ──> [HITL Gate 1: Curriculum Board]       |
+-------------------------------------------┬-------------------------------------------+
                                            │ Emits Locked Learning Units
                                            ▼
+---------------------------------------------------------------------------------------+
|                               2. ASSESSMENT DISPATCH ENGINE                           |
| Topic Completed ──> Item Bank Selector ──> Typst Compiler ──> [HITL Gate 2: Teacher]  |
+-------------------------------------------┬-------------------------------------------+
                                            │ Batched Print + QR/ArUco
                                            ▼
+---------------------------------------------------------------------------------------+
|                           3. VISION DIAGNOSTIC & GRADING ENGINE                       |
| Feeder Scan ──> OpenCV Align ──> Surya OCR ──> Vision LLM ──> [HITL Gate 3: Triage]   |
+-------------------------------------------┬-------------------------------------------+
                                            │ Cognitive Error Tags & Scores
                                            ▼
+---------------------------------------------------------------------------------------+
|                         4. STUDENT KUNDLI (KNOWLEDGE GRAPH)                           |
| PyBKT Engine ──> Longitudinal Skill Matrix (N-10) ──> Term Dossier ──> [HITL Gate 4]  |
+-------------------------------------------▲-------------------------------------------+
                                            │ Structured Behavioral Vectors
                                            │
+-------------------------------------------┴-------------------------------------------+
|                          5. AMBIENT TEACHER VOICE INTAKE ENGINE                       |
| Daily Voice Memo ──> Faster-Whisper ──> Pydantic Extractor ──> [HITL Gate 5: Quick-Tap]|
+---------------------------------------------------------------------------------------+
```

---

### Workflow 1: Curriculum & Experiential Pedagogy Engine

* **Objective:** Ingest national/state boards (CBSE, NCERT, ICSE) and output granular, active-learning lesson kits mapped across 4 mastery tiers (Foundational, Developing, Proficient, Advanced).
* **N-10 Progression Adaptation:**
  * *Nursery–Grade 2:* Focus on tactile, sensorimotor, oral, and play-based activities.
  * *Grades 3–7:* Blended experiential tasks, peer investigation, and semi-formal notebook documentation.
  * *Grades 8–10:* Rigorous concept-to-application experiments strictly tied to board examination rubrics.

#### Step-by-Step Workflow
1. **Curriculum Ingestion:** Admin uploads NCERT/CBSE PDF syllabi or uses pre-loaded curriculum ontologies.
2. **Skill Graph Decomposition:** Agent decomposes chapters into atomic Learning Outcomes (LOs) using Bloom’s Revised Taxonomy.
3. **Pedagogy Synthesis Agent:** Generates a structured JSON unit containing:
   * Experiential Game / Activity description (indoor/outdoor).
   * Bill of Materials (BOM) needed 48 hours in advance by operations.
   * Observable Success Indicators for the teacher during class.
   * NCERT textbook page/exercise cross-references.
4. **Storage:** Stored in a graph database as linked nodes (`Subject -> Grade -> Chapter -> LO -> Mastery Level`).

#### HITL Gate 1: Curriculum Team Review Portal
* **Trigger:** New unit or prompt revision generated.
* **Interface:** Side-by-side diff editor showing the textbook syllabus on the left and the AI-generated activity kit on the right.
* **Action:** Curriculum lead edits, regenerates specific sections (e.g., "make the outdoor game feasible for a rainy day"), and clicks **"Approve & Lock"**. 
* **Rule:** No unapproved pedagogy can be scheduled into the school master calendar.

---

### Workflow 2: Dynamic Differentiated Assessment Dispatch

* **Objective:** Generate individualized, printable paper assessments with unique fiducials and tracking markers.
* **Paper Serialization Mechanism:** Every sheet contains:
  * Top-Right: Quick-Response (DataMatrix/QR) code encoding `(StudentID, AssessmentID, PageNum)`.
  * Four Corners: ArUco visual fiducial markers for precise de-skewing and crop calibration.

#### Step-by-Step Workflow
1. **Trigger Event:** Teacher marks a topic unit as "Completed" on their class dashboard.
2. **Cohort State Retrieval:** System queries the Student Kundli for the class roster.
3. **Adaptive Item Allocation:**
   * 70% Core Cohort Questions (grade-level proficiency verification).
   * 30% Individualized Adaptive Questions (remediation of previously failed prerequisites or advanced extension problems).
4. **Programmatic Document Compilation:** Content is piped into **Typst** (lightning-fast document compiler) to generate print-ready PDFs with fixed, pre-calibrated answer boxes.
5. **Print Dispatch:** Automatically routed to the school's high-speed network printer, pre-collated by classroom and roll number.

#### HITL Gate 2: Teacher Batch Confirmation
* **Trigger:** PDF batch generated 24 hours before scheduled test.
* **Interface:** Mobile or web notification: *"32 assessments compiled for Class 4A (Fractions). 4 students assigned level-1 scaffolding."*
* **Action:** Teacher performs a 30-second review of the auto-assigned difficulty distribution and taps **"Approve & Print"**.

---

### Workflow 3: Computer Vision Diagnostic & Cognitive Grading

* **Objective:** Ingest photos/feeder scans of handwritten student worksheets, grade them line-by-line, and diagnose root-cause cognitive traps.

#### Step-by-Step Workflow
1. **Batch Scan Ingestion:** Mobile app photo or office flatbed scanner outputs a multi-page PDF/TIFF.
2. **Geometric Normalization:**
   * OpenCV detects the four ArUco corner markers.
   * Applies perspective transform and de-skewing to normalize orientation and resolution to a standard $2480 \times 3508$ canvas.
3. **Metadata Extraction:** QR/DataMatrix is decoded to retrieve `StudentID`, `AssessmentID`, and the exact bounding-box coordinates for each question.
4. **Answer Segmentation:** OpenCV slices each answer region into an isolated sub-image.
5. **Cognitive Parsing & Error Classification:**
   * Extracted crop + standard rubric + question metadata sent to the vision reasoning model.
   * Model outputs structured assessment JSON:
     * Numerical Score.
     * Transcription of handwritten work.
     * Step-level error identification (e.g., `Arithmetic Error`, `Conceptual Gap: Subtraction with Borrowing across Zero`, `Illegible Handwriting`).
6. **Kundli State Update:** Numerical scores update the academic mastery vector; diagnostic error tags are added to the remediation queue.

#### HITL Gate 3: Exception-Only Grading Triage
* **Trigger:** Triggered **only** when:
  * Model confidence score drops below 85%.
  * Handwriting is flagged as ambiguous or illegible.
  * Student score on a problem diverges significantly from their historical rolling average ($\pm 2.5\sigma$).
* **Interface:** Web/Mobile "Triage Queue". Shows a zoomed crop of the student's handwritten work side-by-side with the AI's proposed score and error tag.
* **Action:** Teacher taps one of three buttons: **[Accept]**, **[Override Score]**, or **[Re-evaluate with Custom Note]**. Clean sheets are never shown to the teacher, reducing grading overhead by >90%.

---

### Workflow 4: Ambient Teacher Voice Intake (Qualitative Observations)

* **Objective:** Capture qualitative behavioral, emotional, and motor-skill observations without burdening teachers with paperwork.

#### Step-by-Step Workflow
1. **Audio Recording:** At the end of the day or period, the teacher records a 60–120 second unstructured audio memo:
   > *"Today in Class 3B, during the balance scale activity, Kabir showed great spatial intuition but struggled holding the tweezers. Vivaan and Ananya had an argument over sharing blocks; Ananya ended up crying and withdrew from the group. Rohan grasped the concept of weight equivalence instantly."*
2. **High-Speed Transcription:** Audio is sent to a self-hosted **Faster-Whisper** engine with a custom prompt containing the classroom student roster for accurate phoneme recognition.
3. **Structured Entity & Sentiment Parsing:** Transcript is parsed by a low-cost LLM using Pydantic structured extraction:
   * `Student`: Kabir $\rightarrow$ `Domain`: Fine Motor $\rightarrow$ `Observation`: Tweezers handling issue $\rightarrow$ `Sentiment`: Neutral.
   * `Student`: Ananya $\rightarrow$ `Domain`: Socio-Emotional $\rightarrow$ `Observation`: Peer conflict, withdrawn $\rightarrow$ `Action Flag`: Check-in tomorrow.
   * `Student`: Rohan $\rightarrow$ `Domain`: Cognitive Mastery $\rightarrow$ `Observation`: Weight equivalence $\rightarrow$ `Mastery Shift`: Accelerated.
4. **Knowledge Graph Graph Sync:** Observations appended as time-stamped edges to the respective child's graph node.

#### HITL Gate 4: Quick-Tap Entity Disambiguation
* **Trigger:** Audio mentions a student with an ambiguous or duplicate name (e.g., two "Kabirs" in the same class) or an unrecognized name.
* **Interface:** Push notification with an actionable dialog: *"Did you mean Kabir Sharma or Kabir Verma for 'struggled with tweezers'?"*
* **Action:** Single-tap selection resolves the entity and writes the record to the graph.

---

### Workflow 5: Student "Kundli" & Longitudinal Handover Engine

* **Objective:** Synthesize longitudinal cognitive mastery, physical development, and socio-emotional profiles from Nursery through Grade 10, generating automated handover dossiers and parent reports.

#### Step-by-Step Workflow
1. **Mastery Calculation:** Academic progression is calculated using **Bayesian Knowledge Tracing (pyBKT)**:
   $$P(L_t) = P(L_{t-1}) \cdot \frac{1 - P(S)}{P(L_{t-1}) \cdot (1 - P(S)) + (1 - P(L_{t-1})) \cdot P(G)}$$
   *(Accounts for the probability of slips $S$ and guesses $G$ to determine true skill mastery $L_t$.)*
2. **Behavioral Time-Decay:** Qualitative voice tags decay exponentially ($t_{1/2} = 90\text{ days}$) to prevent early negative labels from permanently biasing a child's record.
3. **Annual Handover Generation:** At the end of the academic year, an agent synthesizes:
   * Academic mastery gaps and acceleration areas.
   * Proven pedagogical styles that worked best for the child.
   * Social dynamics, emotional triggers, and successful de-escalation strategies.
4. **Parent Report Card Compilation:** Generates empathetic, strengths-based, jargon-free narrative progress reports mapped to NEP/CBSE holistic progress card (HPC) formats.

#### HITL Gate 5: Year-End Class Teacher Sign-Off
* **Trigger:** Annual handover or term report generated.
* **Interface:** Narrative preview with editable paragraph blocks and a summary of academic trajectory vs. holistic goals.
* **Action:** Class teacher edits the personalized opening note, adjusts any sensitive behavioral notes, and signs off.

---

## 3. Agentic & Orchestration Framework Selection

Choosing the right orchestration framework is critical to prevent spaghetti code. The system requires two distinct layers:

```
+-------------------------------------------------------------------------------+
|                      SYSTEM LAYER 1: DURABLE WORKFLOWS                         |
|                 Temporal.io (State Machine / Task Queues)                     |
|  - Manages multi-day / multi-week lifecycles (Assessment -> Scan -> Handover)  |
|  - Guarantees reliability, retries, approval timeouts, and event sleep states |
+---------------------------------------┬---------------------------------------+
                                        │ Triggers Atomic Agents
                                        ▼
+-------------------------------------------------------------------------------+
|                      SYSTEM LAYER 2: INTRA-AGENT REASONING                    |
|                        LangGraph (Deterministic Graphs)                       |
|  - Cyclical agent loops (e.g., Question Generation -> Linting -> IRT Check)    |
|  - Native Python Pydantic state typing with strict step boundaries            |
+-------------------------------------------------------------------------------+
```

### Why NOT CrewAI or AutoGen?
* **CrewAI / AutoGen:** Highly conversational, non-deterministic, hard to test, token-inefficient, and prone to endless chat loops between agents.
* **Temporal + LangGraph (Selected):**
  * **Temporal** provides ironclad, durable execution. If a teacher takes 4 days to approve an assessment, the Temporal workflow simply sleeps at zero CPU/RAM cost and resumes upon receipt of the approval webhook.
  * **LangGraph** allows cyclical loops for specific tasks (e.g., generating an assessment question, running automated schema checks, and regenerating if it violates constraints) with deterministic control flow.

---

## 4. LLM Routing Matrix & Cost-Minimization Architecture

To operate sustainably at scale, inference costs must not exceed **$0.30 - $0.50 per student per month**. Standard practice using frontier models (e.g., GPT-4o) for all tasks would cost $5.00–$15.00 per student per month.

### 4-Tier Model Routing Table

| Tier | Model | Best For | Input Cost / 1M Tokens | Output Cost / 1M Tokens |
| :--- | :--- | :--- | :--- | :--- |
| **Tier 0: Local/Open-Source** | Faster-Whisper, Surya OCR | Audio transcription, document de-skewing, bounding box cropping | **$0.00** (Runs on small self-hosted GPU node) | **$0.00** |
| **Tier 1: High-Speed Multimodal** | Gemini 2.0 Flash / GPT-4o-mini | Vision grading, teacher voice NER parsing, question bank variations | **$0.10** | **$0.40** |
| **Tier 2: Reasoning Models** | DeepSeek-R1 / Claude 3.5 Haiku | Complex step-by-step math proof evaluation, rubric edge cases | **$0.55** | **$2.19** |
| **Tier 3: Creative Synthesis** | Claude 3.5 Sonnet / GPT-4o | Master prompt refinement, annual holistic handover dossiers | **$3.00** | **$15.00** |

```
                               Incoming Request
                                      │
                                      ▼
                        LiteLLM Proxy Router & Cache
                                      │
             ┌────────────────────────┼────────────────────────┐
             ▼                        ▼                        ▼
        [Audio/OCR]           [Vision Grading/NER]     [Pedagogy/Reports]
           Tier 0                   Tier 1                   Tier 3
       Faster-Whisper /        Gemini 2.0 Flash /      Claude 3.5 Sonnet
          Surya               GPT-4o-mini / DeepSeek
      ($0.00 Server)             ($0.10 / 1M)             ($3.00 / 1M)
```

### Cost Minimization Strategies
1. **Semantic Caching (Redis + GPTCache):** Core curriculum units and standard NCERT question banks are generated once and cached. Repeated requests hit Redis with $0.00 token cost.
2. **Context Clipping:** In Vision Evaluation, never feed the entire full-page scan to the LLM. OpenCV crops *only* the specific question-and-answer box ($200\times 400\text{ px}$ image patch), cutting vision token consumption by 85%.
3. **Structured Outputs via JSON Schema:** Using strict Pydantic grammars avoids conversational model chatter, reducing output token bloat by 60%.

---

## 5. The "Zero-Bespoke-Code" Open-Source Stack

Rather than writing thousands of lines of bespoke infrastructure, assemble these established open-source libraries:

```
+-------------------+----------------------------------------+-------------------------------------------------------+
| Domain            | Open-Source Library / Tool             | Exact Responsibility in SchoolOS                      |
+-------------------+----------------------------------------+-------------------------------------------------------+
| Orchestration     | Temporal (Python SDK)                  | Long-running school lifecycle state machines & HITL   |
| Agent Framework   | LangGraph                              | Multi-step question generation and validation loops   |
| Model Gateway     | LiteLLM Proxy                          | Unified API, dynamic model routing, spend limits      |
| Document Compiler | Typst (`typst-py`)                     | Compiling pixel-perfect printable PDFs with fiducials |
| Vision / Rectify  | OpenCV (`opencv-python-headless`)      | ArUco marker detection, perspective unwarping         |
| Document OCR      | Surya (`VikParuchuri/surya`)           | Layout analysis and text line detection               |
| Voice Transcribe  | Faster-Whisper (`SYSTRAN`)             | Self-hosted, low-latency audio transcription          |
| Mastery Tracing   | pyBKT (`CAHLR/pyBKT`)                  | Bayesian Knowledge Tracing for skill state tracking   |
| Graph Database    | Neo4j Community / Memgraph             | Modeling K-10 skills, topics, and student Kundli      |
| Observability     | Langfuse                               | Tracking prompt accuracy, token costs, and latency    |
+-------------------+----------------------------------------+-------------------------------------------------------+
```

---

## 6. Data Contracts & Schemas

The system relies on clean, immutable Pydantic schemas shared across services.

### Schema 1: The Diagnostic Vision Assessment Output
```python
from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum

class ErrorCategory(str, Enum):
    NONE = "none"
    ARITHMETIC = "arithmetic"
    CONCEPTUAL_PREREQUISITE = "conceptual_prerequisite"
    TRANSCRIPTION_MISREAD = "transcription_misread"
    STEP_OMISSION = "step_omission"

class StepAnalysis(BaseModel):
    step_number: int
    transcribed_work: str = Field(description="Handwritten text extracted for this step")
    is_correct: bool
    detected_error: ErrorCategory
    diagnostic_comment: Optional[str] = Field(description="Root cause analysis of the error")

class QuestionEvaluation(BaseModel):
    question_id: str
    student_id: str
    awarded_score: float
    max_score: float
    confidence_score: float = Field(description="0.0 to 1.0 confidence of the grading model")
    misconception_code: Optional[str] = Field(description="Standardized misconception taxonomy ID")
    steps: List[StepAnalysis]
    requires_human_triage: bool
```

### Schema 2: Ambient Voice Observation Extraction
```python
class ObservationDomain(str, Enum):
    COGNITIVE = "cognitive"
    FINE_MOTOR = "fine_motor"
    GROSS_MOTOR = "gross_motor"
    SOCIO_EMOTIONAL = "socio_emotional"
    BEHAVIORAL = "behavioral"

class ParsedStudentObservation(BaseModel):
    student_name: str
    resolved_student_id: Optional[str] = None
    confidence_in_identity: float
    domain: ObservationDomain
    observation_summary: str
    actionable_followup: Optional[str] = None
    sentiment_valence: float = Field(description="-1.0 (very negative) to +1.0 (very positive)")

class DailyVoiceIntakePayload(BaseModel):
    teacher_id: str
    class_id: str
    audio_duration_seconds: float
    raw_transcript: str
    observations: List[ParsedStudentObservation]
    needs_disambiguation: bool
```

---

## 7. Lean Implementation Roadmap (MVP in 8 Weeks)

```
   Week 1-2: Core Engine & Graph Setup
   ├── Ingest CBSE/NCERT Grade 3-5 Math syllabus into Neo4j
   ├── Stand up LiteLLM proxy with Gemini Flash & Claude Haiku
   └── Deploy basic LangGraph pedagogy generator

   Week 3-4: Printable Assessment Pipeline
   ├── Build Typst templates with ArUco corners and DataMatrix
   ├── Implement automated PDF rendering service
   └── Build basic Teacher Assessment Dispatcher UI

   Week 5-6: Diagnostic Vision Evaluation
   ├── Build OpenCV de-skewing and cropping pipeline
   ├── Wire up multimodal prompt for math error diagnosis
   └── Implement the web-based Teacher Triage Queue (HITL Gate 3)

   Week 7-8: Ambient Voice Intake & Kundli Pilot
   ├── Deploy Faster-Whisper container for audio memos
   ├── Integrate Pydantic NER pipeline into Neo4j
   └── Run 2-week live pilot with 2 teachers across 60 students
```

---

## 8. Summary of Solved Architectural Bottlenecks

1. **No Monolithic Bloat:** All complex tasks are delegated to battle-tested micro-engines (OpenCV for vision alignment, Typst for PDFs, Faster-Whisper for STT, pyBKT for mastery tracking).
2. **Sub-Cent Operating Economics:** By restricting vision LLMs to isolated, cropped bounding boxes and routing bulk tasks to sub-cent models, total monthly inference is kept under **$0.40 per student**.
3. **True Human-in-the-Loop without Teacher Fatigue:** Routine activities run automatically, while human expertise is focused strictly on approval gates, edge cases, and high-leverage exceptions.