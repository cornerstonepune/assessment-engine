"""N8 — a scan arrives on its own: from a Drive link, into the engine's inbox, sorted and read (ARCHITECTURE.md §2,
SPEC "Drive trigger on the capture folder → engine"). Nobody pastes a command: the site's "Read a scan" form and the
n8n Drive-folder flow (`n8n/workflows/f3-read-scans.json`) both hand the engine a link, and the engine does the rest —
fetches the file to `~/cornerstone/assessments/inbox`, sorts its pages by code (`sorting`), reads and marks every copy
whose code names its child (`copies.read`), and puts the answers on Marking.

What arrives is a link, never the file: the file stays on Drive and in the assessments folder, never in the database
or the repository (rule 6). A copy printed bare — no child's code — is reported, not guessed at.
"""

import re
import urllib.request
from pathlib import Path

from engine.core import db
from engine.w3_read import copies, read_eval

INBOX = Path(read_eval.ASSESSMENTS).expanduser() / "inbox"
FLOW = "read-scan"
# a Drive link as people paste it: /file/d/<id>/view, open?id=<id>, uc?id=<id>&export=download
_DRIVE = re.compile(r"(?:/file/d/|[?&]id=)([A-Za-z0-9_-]{20,})")
_NAME = re.compile(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)')
MOST = 64 * 1024 * 1024  # a scan of a class is 10-20 MB; a file larger than this is not one


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
    name = Path(named.group(1)).name if named else f"{fid}.pdf"
    if not name.lower().endswith(".pdf"):
        name += ".pdf"
    INBOX.mkdir(parents=True, exist_ok=True)
    out = INBOX / name
    if out.exists() and out.read_bytes() != data:  # a different file of the same name: keep both
        out = INBOX / f"{out.stem}-{fid[:6]}.pdf"
    out.write_bytes(data)
    return out


def start(conn, tenant, path: Path, actor: str) -> str:
    """The run a person or a flow can look at (`/runs/{id}`): what the engine is doing with this file."""
    return str(
        conn.execute(
            "insert into flow_run (tenant_id, flow, trigger) values (%s, %s, %s) returning id",
            (tenant, FLOW, f"{actor}: {path.name}"),
        ).fetchone()["id"]
    )


def read(run_id: str, path: Path, actor: str) -> list[dict]:
    """Every copy in the file read for its child, on its own connection (this runs after the request that
    accepted the file has answered), the run marked ok or error with what happened."""
    with db.connect() as conn:
        try:
            out = copies.read(conn, str(path), "", None, actor)
            conn.execute(
                "update flow_run set status = 'ok', finished_at = now(), updated_at = now() where id = %s",
                (run_id,),
            )
            return out
        except Exception as e:  # the run says why; the request that started it has long since answered
            conn.rollback()
            conn.execute(
                "update flow_run set status = 'error', error = %s, finished_at = now(), updated_at = now()"
                " where id = %s",
                (str(e)[:2000], run_id),
            )
            raise
