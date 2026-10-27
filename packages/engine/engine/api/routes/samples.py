"""W1/N1 — an educator changes an English skill's samples and the kinds its levels ask, over HTTP
(goals/edt_edit_samples_and_kinds.yaml). The engine checks every sample before it stores it and answers in words what
failed; the website shows those words beside the field and keeps what the educator typed."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from engine.api.deps import get_conn, require_engine_key
from engine.w1_bank import english_edit, english_form, generate, retire

router = APIRouter(dependencies=[Depends(require_engine_key)])
Text = Field(default="", max_length=4000)


class SampleFields(BaseModel):
    """The form's words, one line per item where a list is asked (engine/w1_bank/english_form.py)."""

    ask: str = Field(default="", max_length=600)
    text: str = Text
    options: str = Text
    left: str = Text
    right: str = Text
    answer: str = Text
    accept: str = Text
    key_points: str = Text
    not_words: str = Text


class WrongAnswer(BaseModel):
    answer: str = Field(default="", max_length=600)
    mistake_code: str = Field(default="", max_length=80)


class SampleForm(BaseModel):
    fields: SampleFields
    wrong: list[WrongAnswer] = Field(default_factory=list, max_length=12)
    passage_code: str | None = Field(default=None, max_length=80)
    passage_title: str | None = Field(default=None, max_length=200)
    passage_text: str | None = Field(default=None, max_length=8000)
    rubric_code: str | None = Field(default=None, max_length=80)


class Where(BaseModel):
    """Which level and kind a change is to, and who makes it."""

    level: str = Field(min_length=1, max_length=20)
    kind: str = Field(min_length=1, max_length=40)
    by: str = Field(min_length=1, max_length=200)


class SampleSaveRequest(SampleForm, Where):
    ord: int | None = Field(default=None, ge=1)


class SampleRemoveRequest(Where):
    ord: int = Field(ge=1)


class KindAddRequest(Where):
    samples: list[SampleForm] = Field(default_factory=list, max_length=6)


class KindRemoveRequest(Where):
    pass


class MoreRequest(Where):
    """More questions like English sample `ord`; how many is checked against its row by the engine."""

    ord: int = Field(ge=1)
    n: int = Field(ge=1, le=100)


class MathsMoreRequest(BaseModel):
    """More questions like a typed Maths sum, in a line or in columns."""

    level: str = Field(min_length=1, max_length=20)
    text: str = Field(min_length=1, max_length=40)
    layout: str = Field(pattern="^(line|columns)$")
    n: int = Field(ge=1, le=100)
    by: str = Field(min_length=1, max_length=200)


class KindStopRequest(BaseModel):
    """A kind stopped, or used again, at one level, or at every level that asks it (no level)."""

    level: str | None = Field(default=None, min_length=1, max_length=20)
    kind: str = Field(min_length=1, max_length=40)
    by: str = Field(min_length=1, max_length=200)


def _form(f: SampleForm) -> dict[str, Any]:
    return {**f.model_dump(include={"passage_code", "passage_title", "passage_text", "rubric_code"}),
            "fields": f.fields.model_dump(), "wrong": [w.model_dump() for w in f.wrong]}  # fmt: skip


@router.get("/skill/{code}/sample/form")
def sample_form(code: str, level: str, kind: str, ord: int, conn=Depends(get_conn, scope="function")):
    """One sample as the educator's form shows it: its words one line per item, its wrong answers, passage and rubric."""
    s = english_edit.current(conn, code, level, kind, ord)
    if not s:
        raise HTTPException(404, "That sample is not on this level any more.")
    return {
        "fields": english_form.to_form(kind, s),
        "wrong": [{"answer": w["answer"], "mistake_code": w["mistake_code"]} for w in s["wrong"]],
        "passage_code": s["passage_code"],
        "rubric_code": s["rubric_code"],
    }


@router.post("/skill/{code}/sample")
def save_sample(code: str, body: SampleSaveRequest, conn=Depends(get_conn, scope="function")):
    """One sample changed (`ord`) or added (no `ord`): {saved, ord, faults by field, in words}."""
    return english_edit.save(conn, code, body.level, body.kind, body.ord, body.by, **_form(body))


@router.post("/skill/{code}/sample/remove")
def remove_sample(code: str, body: SampleRemoveRequest, conn=Depends(get_conn, scope="function")):
    return english_edit.remove(conn, code, body.level, body.kind, body.ord, body.by)


@router.post("/skill/{code}/kind")
def add_kind(code: str, body: KindAddRequest, conn=Depends(get_conn, scope="function")):
    """A kind added to a level with the samples it needs: {saved, why, faults per sample}."""
    return english_edit.add_kind(conn, code, body.level, body.kind, [_form(s) for s in body.samples], body.by)


@router.post("/skill/{code}/kind/remove")
def remove_kind(code: str, body: KindRemoveRequest, conn=Depends(get_conn, scope="function")):
    return english_edit.remove_kind(conn, code, body.level, body.kind, body.by)


@router.get("/skill/{code}/kind/touches")
def kind_touches(code: str, kind: str, level: str | None = None, conn=Depends(get_conn, scope="function")):
    """What stopping a kind would touch, writing nothing: {levels, questions, papers, withdraw}."""
    return retire.touches(conn, code, kind, level)


@router.post("/skill/{code}/kind/stop")
def stop_kind(code: str, body: KindStopRequest, conn=Depends(get_conn, scope="function")):
    """A kind stopped: {stopped, why, levels, questions, papers, withdrawn}."""
    return retire.stop(conn, code, body.kind, body.by, body.level)


@router.post("/skill/{code}/kind/start")
def start_kind(code: str, body: KindStopRequest, conn=Depends(get_conn, scope="function")):
    """A stopped kind used again: {started, why, levels}."""
    return retire.start(conn, code, body.kind, body.by, body.level)


@router.post("/skill/{code}/sample/more")
def more_english(code: str, body: MoreRequest, conn=Depends(get_conn, scope="function")):
    """Questions like an English sample, each checked by code: {made, why, returned, kept, thrown, ords}."""
    return generate.english(conn, code, body.level, body.kind, body.ord, body.n, body.by)


@router.post("/skill/{code}/maths/more")
def more_maths(code: str, body: MathsMoreRequest, conn=Depends(get_conn, scope="function")):
    """Questions like a typed Maths sum, made by code: {made, why, cases, kept, sample}."""
    return generate.maths(conn, code, body.level, body.text, body.layout, body.n, body.by)
