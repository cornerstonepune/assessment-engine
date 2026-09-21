"""Request and response shapes for every route. Every field is an id, a count, a path, or a
code — never a name, and never the content of what a child wrote (rule 6): n8n receives these
bodies and logs every one of them, so the detail a person needs to review an import lives in the
app, which reads the database directly, not in what a workflow's execution history retains."""

from typing import Literal

from pydantic import BaseModel, Field


class FindChildRequest(BaseModel):
    section: str
    first_name: str
    actor: str


class FindChildResponse(BaseModel):
    child_id: str


class IngestRequest(BaseModel):
    # `path` matches `legacy.import_scan`'s existing parameter and `capture.path`'s existing
    # column — both already carry a filename that can include a child's name, unchanged here.
    # D2 (docs/superpowers/plans/2026-09-18-spine.md) forbids a name-bearing path in what n8n
    # *logs*; that is a chunk 4 workflow-design and execution-data-retention decision, not
    # something this request shape can enforce on its own — flagged in HANDOFF.md.
    path: str
    paper_code: str
    child_id: str
    actor: str
    pages: list[int] | None = None
    masks: dict[int, float] | None = None
    narrative: bool = False


class IngestResponse(BaseModel):
    capture_id: str
    pages: int
    n_results: int
    n_unmatched: int
    n_notes: int
    already: bool = False


class MarkRequest(BaseModel):
    child_id: str


class MarkResponse(BaseModel):
    changed: int
    already: bool = False


class CommitRequest(BaseModel):
    child_id: str
    by: str


class CommitResponse(BaseModel):
    confirmed: int
    already: bool = False


class CorrectRequest(BaseModel):
    result_id: str
    human_read: str
    by: str


class CorrectResponse(BaseModel):
    status: str
    codes: list[str]
    was: str
    now: str


class GraphRebuildRequest(BaseModel):
    child_id: str | None = None


class GraphRebuildResponse(BaseModel):
    states: int
    already: bool = False


class BankFillRequest(BaseModel):
    skill_set: str
    difficulty: str
    count: int = Field(gt=0, le=200)


class BankFillResponse(BaseModel):
    counts: dict[str, int]
    reasons: dict[str, int]
    accepted_item_keys: list[str]
    already: bool = False


class BankCorrectRequest(BaseModel):
    stem: str = Field(min_length=1, max_length=600)
    by: str = Field(min_length=1, max_length=200)
    reason: str = Field(max_length=300)


class BankCorrectResponse(BaseModel):
    item_key: str
    retired: str


class BankRemoveRequest(BaseModel):
    by: str = Field(min_length=1, max_length=200)
    note: str = Field(max_length=300)


class BankRemoveResponse(BaseModel):
    item_key: str
    status: str
    worksheets_retired: int


class BankCoverageRow(BaseModel):
    code: str
    difficulty: str
    n: int
    target: int
    shortfall: int


class BankReviewRequest(BaseModel):
    skill_set: str
    difficulty: str
    reviewer: Literal["pedagogy_review", "language_review"]


class BankReviewResponse(BaseModel):
    skill_set: str
    difficulty: str
    reviewer: str
    judged: int
    not_passed: int
    model: str | None = None
    cost_inr: float = 0
    already: bool = False


class RunResponse(BaseModel):
    id: str
    flow: str
    trigger: str | None
    status: str
    error: str | None
    tokens: int | None
    cost_inr: float | None


class WeekPrescribeRequest(BaseModel):
    section: str
    week: str
    skill_set: str
    kind: str = "practice"


class WeekPrescribeResponse(BaseModel):
    section: str
    week: str
    kind: str
    prescribed: int
    by_rule: dict[str, int]
    by_difficulty: dict[str, int]
    already: bool = False


class WeekAssembleRequest(BaseModel):
    section: str
    week: str
    kind: str = "practice"


class WeekAssembleResponse(BaseModel):
    section: str
    week: str
    kind: str
    sheets: int
    spares: int
    short: list[dict]
    qr_codes: list[str]
    already: bool = False


class WeekRenderRequest(BaseModel):
    section: str
    week: str
    kind: str = "practice"
    out: str = "data/packs"
    actor: str = "n8n"


class WeekRenderResponse(BaseModel):
    section: str
    week: str
    kind: str
    pack_path: str
    pages: int
    sheets: int
    spares: int
    short: list[dict]
    already: bool = False


class WeekApproveRequest(BaseModel):
    section: str
    week: str
    kind: str = "practice"
    by: str


class WeekApproveResponse(BaseModel):
    section: str
    week: str
    kind: str
    approved_by: str
    sheets: int
    named: int
    spares: int
    qr_codes: list[str]
    already: bool = False
