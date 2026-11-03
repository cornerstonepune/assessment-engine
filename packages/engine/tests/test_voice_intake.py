"""K2 voice notes (goals/m1-01-voice-intake.yaml). Step 1: the recording never reaches git."""

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
AUDIO = (".m4a", ".mp3", ".wav", ".ogg", ".opus", ".webm", ".aac", ".flac")


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=False)


def test_git_refuses_every_kind_of_voice_recording_and_holds_none():
    for ext in AUDIO:
        assert _git("check-ignore", "-q", f"anywhere/note{ext}").returncode == 0, (
            f"git would keep a {ext} file"
        )
    tracked = _git("ls-files").stdout.splitlines()
    assert [p for p in tracked if p.lower().endswith(AUDIO)] == []
