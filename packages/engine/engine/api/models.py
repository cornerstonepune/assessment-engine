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
