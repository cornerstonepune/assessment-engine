"""The engine as a service (ADR 0008): n8n's entire vocabulary from `ARCHITECTURE.md` §5, the
part of it built so far. Every route below `require_engine_key` is thin — it fills a request
model, runs it through `run_idempotent`, and shapes the result. No route contains a decision;
every decision is the function it calls, which is also what the CLI calls, which is also what the
tests in `tests/` already cover. This file only wires."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from engine.api.idempotency import InProgress
from engine.api.routes import bank, capture, children, focus, graph, library, runs, week
from engine.w3_read import inbox


@asynccontextmanager
async def lifespan(app: FastAPI):
    # a scan being read when the engine stopped was read by the process that stopped: say so on its run
    try:
        inbox.orphaned()
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


@app.exception_handler(InProgress)
def in_progress(request: Request, exc: InProgress) -> JSONResponse:
    # A genuine concurrent duplicate (the same Idempotency-Key arrived twice before the first
    # finished) is the caller's to retry, not this process's to guess at — 409, not 500.
    return JSONResponse(status_code=409, content={"detail": str(exc)})
