"""Where a K2 voice note's recording is kept (task M1-01): the engine box's own disk, under the gitignored `data/`
folder, as scans are (`data/scans`). Only the key, `voice/<year>/<note id>.<ext>`, is in the database; the recording
never enters git (`.gitignore` refuses audio) or a log. How long a recording is kept is O-14, open: config row
`voice.audio_retention_days`, null keeps it (`engine read voice retention`)."""

import re
import uuid
from pathlib import Path

from engine.core import db

ROOT = db.REPO_ROOT / "data"
KINDS = {".m4a", ".mp3", ".wav", ".ogg", ".opus", ".webm", ".aac", ".mp4", ".flac"}
MOST = 10 * 2**20  # a note is under a minute; ten megabytes holds several at a phone's quality
KEY = re.compile(r"^voice/\d{4}/[0-9a-f-]{36}\.[a-z0-9]{2,4}$")


class Refused(Exception):
    """A recording not taken in, with the words the page shows and the HTTP code."""

    def __init__(self, words: str, status: int = 422):
        super().__init__(words)
        self.status = status


def key_for(note_id: uuid.UUID, filename: str, year: int) -> str:
    ext = Path(filename or "").suffix.lower()
    if ext not in KINDS:
        raise Refused("Not sent. That is not a recording this page can keep.", 415)
    return f"voice/{year}/{note_id}{ext}"


def path(key: str) -> Path:
    """The file a key names; a key that is not one of ours names nothing (no path outside `data/voice`)."""
    if not KEY.fullmatch(key):
        raise Refused("not a recording's key", 404)
    return ROOT / key


def save(key: str, data: bytes) -> None:
    if not data:
        raise Refused("Nothing heard. Record again or use the form.")
    if len(data) > MOST:
        raise Refused("Not sent. That recording is longer than a note.", 413)
    p = path(key)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)


def read(key: str) -> bytes:
    p = path(key)
    if not p.exists():
        raise Refused("This recording is no longer kept.", 404)
    return p.read_bytes()
