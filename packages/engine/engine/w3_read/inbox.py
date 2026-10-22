"""N8 — a scan arrives on its own: from a Drive link, into the engine's inbox, sorted and read (ARCHITECTURE.md §2,
SPEC "Drive trigger on the capture folder → engine"). Nobody pastes a command: the site's "Read a scan" form and the
n8n Drive-folder flow (`n8n/workflows/f3-read-scans.json`) both hand the engine a link, and the engine does the rest —
fetches the file to `~/cornerstone/assessments/inbox`, sorts its pages by code (`sorting`), reads and marks every copy
whose code names its child (`copies.read`), and puts the answers on Marking.

Or the file itself, put in on Marking: the browser sends it straight to the engine (`POST /read/upload`, ADR 0092) — a
PDF as it is, or the photos of one paper's pages, made one PDF here in the order the phone took them (`take`).

The file stays in the assessments folder, never in the database, the repository or a log (rule 6). A copy printed bare
— no child's code — is reported, not guessed at.
"""

import hashlib
import io
import json
import re
import urllib.request
from pathlib import Path

import pillow_heif
import pymupdf
from PIL import Image, ImageOps

from engine.core import db
from engine.w3_read import copies

INBOX = Path(db.ASSESSMENTS).expanduser() / "inbox"
FLOW = "read-scan"
# a Drive link as people paste it: /file/d/<id>/view, open?id=<id>, uc?id=<id>&export=download
_DRIVE = re.compile(r"(?:/file/d/|[?&]id=)([A-Za-z0-9_-]{20,})")
_NAME = re.compile(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)')
MOST = 64 * 1024 * 1024  # a scan of a class is 10-60 MB; a file larger than this is not one
# what a file is, by its first bytes, never by its name: HEIC is an ISO box whose brand names it
_HEIC = (b"heic", b"heix", b"heim", b"heis", b"hevc", b"hevx", b"mif1", b"msf1")
pillow_heif.register_heif_opener()


def kind(data: bytes) -> str | None:
    """ "pdf", "photo", or None for anything else."""
    if data.startswith(b"%PDF"):
        return "pdf"
    if data.startswith((b"\xff\xd8\xff", b"\x89PNG\r\n\x1a\n")) or (
        data[4:8] == b"ftyp" and data[8:12] in _HEIC
    ):
        return "photo"
    return None


def drive_id(url: str) -> str | None:
    m = _DRIVE.search(url or "")
    return m.group(1) if m else None


def _download(url: str):
    """(bytes, the name the server gave the file) — one place that touches the network, stood in for in tests."""
    with urllib.request.urlopen(url, timeout=120) as r:  # noqa: S310 — a Drive address this module built
        return r.read(MOST + 1), _NAME.search(r.headers.get("content-disposition") or "")


def fetch(url: str, download=_download) -> Path:
    """The file a Drive link names, saved in the inbox under its own name. Refuses a link that is not Drive's,
    a file that is not a PDF, and a file too large to be a scan of a class."""
    fid = drive_id(url)
    if not fid:
        raise ValueError("that is not a Google Drive link to a file")
    data, named = download(f"https://drive.google.com/uc?export=download&id={fid}")
    if len(data) > MOST:
        raise ValueError("that file is larger than any scan of a class")
    if not data.startswith(b"%PDF"):
        raise ValueError("that file is not a PDF: is the scan shared with anyone who has the link?")
    return _kept(Path(named.group(1)).name if named else f"{fid}.pdf", data)


def _kept(name: str, data: bytes) -> Path:
    """The PDF saved in the inbox under its own name; a different file of the same name keeps both."""
    name = Path(name).name or "scan.pdf"
    if not name.lower().endswith(".pdf"):
        name += ".pdf"
    INBOX.mkdir(parents=True, exist_ok=True)
    out = INBOX / name
    if out.exists() and out.read_bytes() != data:
        out = INBOX / f"{out.stem}-{hashlib.sha256(data).hexdigest()[:6]}.pdf"
    out.write_bytes(data)
    return out


class Refused(ValueError):
    """What the engine will not take, in words, with the HTTP status that says why."""

    def __init__(self, status: int, why: str):
        super().__init__(why)
        self.status = status


def take(files: list[tuple[str, bytes]]) -> Path:
    """One upload, saved in the inbox: a PDF as it is, or photos (JPG, PNG, HEIC) as one PDF (`_one_paper`). Refuses
    a file that is neither, one larger than any scan of a class, and a PDF sent with anything else (`_checked`)."""
    _checked(files)
    if kind(files[0][1]) == "pdf":
        name, data = files[0]
        try:
            pymupdf.open(stream=data, filetype="pdf").close()
        except Exception as e:
            raise Refused(415, f"{name} is not a PDF or a photo (JPG, PNG or HEIC): it does not open") from e
        return _kept(name, data)
    return _one_paper(files)


def _checked(files: list[tuple[str, bytes]]) -> None:
    """Every file a PDF or a photo, by its first bytes, within the size of a scan of a class; a PDF alone."""
    if not files:
        raise Refused(400, "no file was sent")
    most = f"{MOST // 2**20} MB at most"
    for name, data in files:
        if len(data) > MOST:
            raise Refused(413, f"{name} is larger than any scan of a class ({most})")
        if kind(data) is None:
            raise Refused(415, f"{name} is not a PDF or a photo (JPG, PNG or HEIC)")
    if sum(len(d) for _, d in files) > MOST:
        raise Refused(413, f"these photos are larger together than any scan of a class ({most})")
    if len(files) > 1 and any(kind(d) == "pdf" for _, d in files):
        raise Refused(400, "send a PDF on its own; photos together are one paper")


def _one_paper(photos: list[tuple[str, bytes]]) -> Path:
    """The photos of one paper as one PDF, a page each, in the order of their names: a phone names its photos in the
    order they were taken, so the paper's pages come out in page order. Each turned upright by its EXIF first, which a
    PDF page does not carry."""
    photos = sorted(
        photos, key=lambda f: [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", f[0])]
    )
    doc = pymupdf.open()
    for name, data in photos:
        try:
            img = ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert("RGB")
        except Exception as e:
            raise Refused(415, f"{name} is not a PDF or a photo (JPG, PNG or HEIC): it does not open") from e
        jpg = io.BytesIO()
        img.save(jpg, "JPEG", quality=90)
        page = doc.new_page(width=img.width * 72 / 150, height=img.height * 72 / 150)  # drawn at 150 dpi
        page.insert_image(page.rect, stream=jpg.getvalue())
    return _kept(f"{Path(photos[0][0]).stem}.pdf", doc.tobytes())


def start(tenant, path: Path, actor: str, pages: int | None = None) -> str:
    """The run a person or a flow can look at (`/runs/{id}`): what the engine is doing with this file. Written and
    committed on its own connection, before the reading starts: FastAPI runs a background task BEFORE the
    request's own transaction commits (2026-09-25, the first live run: `/runs/{id}` said "no run" for minutes,
    and the reading could not mark a row it could not see). The file's pages are on it from the start, so Marking can
    say how many were found while the reading goes on."""
    with db.connect() as conn:
        return str(
            db.one(
                conn,
                "insert into flow_run (tenant_id, flow, trigger, result) values (%s, %s, %s, %s::jsonb) returning id",
                (tenant, FLOW, f"{actor}: {path.name}", json.dumps({"pages": pages, "file": path.name})),
            )["id"]
        )


def read(run_id: str, path: Path, actor: str, again: bool = False) -> list[dict]:
    """Every copy in the file read for its child, on its own connection (this runs after the request that
    accepted the file has answered), the run marked ok or error with what happened. What the reading came to is
    kept on the run — each copy read, each not read and why, each page missing or photographed twice — by the
    child's id, never a name (rule 6): until 2026-10-16 it was thrown away, and nobody was told a child's first page
    was not in the file (goals/l11-a-scan-is-read-whole.yaml)."""
    with db.connect() as conn:
        try:
            out = copies.read(
                conn,
                str(path),
                "",
                None,
                actor,
                again=again,
                given=given(conn, path.name),
                progress=_progress(run_id),
            )
            conn.execute(
                "update flow_run set status = 'ok', result = coalesce(result, '{}') || %s::jsonb, finished_at = now(),"
                " updated_at = now()"
                " where id = %s",
                (json.dumps({"copies": out}, default=str), run_id),
            )
            return out
        except Exception as e:  # the run says why; the request that started it has long since answered
            conn.rollback()
            conn.execute(
                "update flow_run set status = 'error', error = %s, finished_at = now(), updated_at = now()"
                " where id = %s",
                (f"{type(e).__name__}: {e}"[:2000], run_id),
            )
            # Committed before the exception leaves: `db.connect` rolls back on the way out of a failure, and took
            # this record with it — the first live run said "running" for 25 minutes after it had died on
            # `ConfigParseError` (2026-09-25).
            conn.commit()
            raise


def _progress(run_id: str):
    """How far the reading has got, written on the run as each copy is read (goals/s2-the-assessment-card.yaml: "page n
    of N, about how long"): on a connection of its own, committed at once, since the reading's own transaction is open
    until the whole file is read. The card says the time left from `at` and the pages still to read."""

    def tell(done: int, of: int) -> None:
        with db.connect() as c:
            c.execute(
                "update flow_run set result = coalesce(result, '{}') || jsonb_build_object('read',"
                " jsonb_build_object('pages', %s::int, 'of', %s::int, 'at', now())), updated_at = now() where id = %s",
                (done, of, run_id),
            )

    return tell


# the file a run read: kept on the run from 2026-10-22, before that only in its trigger ("who: file")
_FILE = "coalesce(result ->> 'file', substr(trigger, strpos(trigger, ': ') + 2))"


def given(conn, name: str) -> dict[int, str]:
    """{page: child} for one file: each page on which no code could be read that a person said is a child's, on any run
    of the file, the latest word on a page standing (goals/ux9a-no-guessed-pages.yaml)."""
    out = {}
    for r in conn.execute(
        f"select result -> 'given' as given from flow_run where flow = %s and {_FILE} = %s"
        " and result ? 'given' order by started_at",
        (FLOW, name),
    ):
        out |= {int(g["page"]): g["child_id"] for g in r["given"]}
    return out


def give(conn, run_id: str, page: int, child_id: str, by: str) -> Path:
    """A person says whose a page with no code is: kept on the file's run, which is marked to be read again (`read`,
    started by the caller), and the file to read. Only a page of the run that waits for its child, given to a child
    whose own paper is in the file, and not while the file is being read."""
    run = conn.execute(
        f"select status, result, {_FILE} as file from flow_run where id = %s and flow = %s for update",
        (run_id, FLOW),
    ).fetchone()
    if not run:
        raise Refused(404, "no such scan")
    if run["status"] == "running":
        raise Refused(409, "this scan is still being read: say whose the page is once it is read")
    result = run["result"] or {}
    lines = result.get("copies") or []
    done = {int(g["page"]) for g in result.get("given") or []}
    waiting = {n for c in lines for n in (c.get("no_code") or [])} - done
    if page not in waiting:
        raise Refused(409, f"page {page} of this file is not one waiting for its child")
    if child_id not in {c["child_id"] for c in lines if c.get("child_id") and c.get("by_code", True)}:
        raise Refused(409, "no paper of that child is in this file, so the page cannot be read as theirs")
    path = INBOX / Path(run["file"]).name
    if not path.exists():
        raise Refused(410, f"{path.name} is no longer kept by the engine: send the scan again")
    word = {"page": page, "child_id": child_id, "by": by}
    conn.execute(
        "update flow_run set status = 'running', error = null, finished_at = null, updated_at = now(),"
        " result = result || jsonb_build_object('given', coalesce(result -> 'given', '[]'::jsonb) || %s::jsonb)"
        " where id = %s",
        (json.dumps([word]), run_id),
    )
    return path


def again(conn, run_id: str) -> tuple[Path, str]:
    """(the file a run read, its tenant) — to be read afresh, as a run of its own (`start`, then `read` with `again`):
    every copy no person has worked on is read anew and its old reading superseded, never edited (rule 4); a person's
    checks stay (`checked`). The same file is otherwise never read twice (`legacy.import_scan`, `file_sha256`). Not
    while the file is being read, and only while the engine still keeps it."""
    run = conn.execute(
        f"select status, tenant_id, {_FILE} as file from flow_run where id = %s and flow = %s", (run_id, FLOW)
    ).fetchone()
    if not run:
        raise Refused(404, "no such scan")
    if run["status"] == "running":
        raise Refused(409, "this scan is still being read: read it again once it is read")
    path = INBOX / Path(run["file"]).name
    if not path.exists():
        raise Refused(410, f"{path.name} is no longer kept by the engine: send the scan again")
    return path, str(run["tenant_id"])


def page_jpg(conn, run_id: str, page_no: int) -> bytes:
    """One page of the file a run read, drawn small: enough for a person to see whose name is on it."""
    run = conn.execute(
        f"select {_FILE} as file from flow_run where id = %s and flow = %s", (run_id, FLOW)
    ).fetchone()
    path = run and INBOX / Path(run["file"]).name
    if not path or not path.exists():
        raise Refused(404, "the scan is not on this machine")
    with pymupdf.open(path) as doc:
        if not 1 <= page_no <= len(doc):
            raise Refused(404, f"the file has no page {page_no}")
        return doc[page_no - 1].get_pixmap(dpi=60).tobytes("jpeg")
