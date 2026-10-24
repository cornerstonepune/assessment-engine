"""The engine as a service (ADR 0008): n8n's entire vocabulary from `ARCHITECTURE.md` §5, the
part of it built so far. Every route below `require_engine_key` is thin — it fills a request
model, runs it through `run_idempotent`, and shapes the result. No route contains a decision;
every decision is the function it calls, which is also what the CLI calls, which is also what the
tests in `tests/` already cover. This file only wires."""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from engine.api.idempotency import InProgress
from engine.api.routes import (
    bank,
    capture,
    card,
    children,
    focus,
    graph,
    library,
    maker,
    parent,
    runs,
    samples,
    upload,
    week,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # a run going when the engine stopped ran in the process that stopped: say so on it. Not in the standby a deploy
    # starts beside a serving engine (deploy/switch.sh): a run going then is that engine's, and still going.
    if not os.getenv("ENGINE_STANDBY"):
        try:
            runs.orphaned()
        except Exception:  # no database at start (tests, a first boot): nothing was running
            pass
    yield


app = FastAPI(title="Cornerstone engine", lifespan=lifespan)

app.include_router(runs.health_router)
app.include_router(runs.runs_router)
app.include_router(children.router)
app.include_router(capture.router)
app.include_router(graph.router)
app.include_router(bank.router)
app.include_router(week.router)
app.include_router(library.router)
app.include_router(focus.router)
app.include_router(maker.router)
app.include_router(card.router)
app.include_router(parent.router)
app.include_router(upload.router)
app.include_router(samples.router)

# A scan is sent by the educator's browser from the site's own address (ADR 0092), so the browser must be let read the
# answer. Any origin: no route trusts a cookie or the caller's address — each asks for the engine's key, or for the
# upload token only the site can sign — so a page elsewhere gains nothing it could not do without a browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST"],
    allow_headers=["x-upload-token"],
    max_age=3600,
)


@app.exception_handler(InProgress)
def in_progress(request: Request, exc: InProgress) -> JSONResponse:
    # A genuine concurrent duplicate (the same Idempotency-Key arrived twice before the first
    # finished) is the caller's to retry, not this process's to guess at — 409, not 500.
    return JSONResponse(status_code=409, content={"detail": str(exc)})
