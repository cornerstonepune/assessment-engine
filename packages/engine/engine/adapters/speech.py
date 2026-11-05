"""The only module that talks to the speech-to-text service: Sarvam AI (Nimish, 2026-11-03; task M1-01).

One call sends one recording and nothing else: no roll, no class, no name. The educator says children as numbers, so
no name is in the audio either (O-13). The words it is told to listen for are the template's own headings, never a
name. The key is the environment variable SARVAM_API_KEY; neither the key, the audio nor the transcript is ever logged
or put in an error. What Sarvam's documentation says (read 3 Nov 2026) and what is not verified:
research/2026-11-03-k2-voice-transcription-spike.md. Before the first real note, the school's Sarvam workspace Owner
sets Data retention to "No retention": Sarvam's default keeps data indefinitely.
"""

import json
import os
from dataclasses import dataclass

import httpx

ENDPOINT = "https://api.sarvam.ai/speech-to-text"  # POST, multipart; key in the header api-subscription-key
MODEL = "saaras:v4"  # Sarvam's default; `keyterms` works only with it. The fixtures may change this.
LANGUAGE = "unknown"  # Sarvam detects; a note mixes Hindi and English. The fixtures may change this.
TIMEOUT_S = 60
MAX_KEYTERMS, MAX_KEYTERM_CHARS = 50, 64  # Sarvam's documented limits


class SpeechError(Exception):
    """The recording could not be turned into words. Says why, never what was said."""


@dataclass(frozen=True)
class Heard:
    transcript: str
    language: str | None
    request_id: str | None


def keyterms(headings: list[str]) -> list[str]:
    """The words Sarvam is told to listen for: the template's headings, within its limits."""
    out = [h for h in dict.fromkeys(headings) if len(h) <= MAX_KEYTERM_CHARS]
    return out[:MAX_KEYTERMS]


def transcribe(
    audio: bytes, filename: str, terms: list[str], client: httpx.Client | None = None, key: str | None = None
) -> Heard:
    key = os.environ.get("SARVAM_API_KEY") if key is None else key
    if not key:
        raise SpeechError("SARVAM_API_KEY is not set")
    form = {"model": MODEL, "language_code": LANGUAGE, "keyterms": json.dumps(keyterms(terms))}
    owned = client is None
    client = client or httpx.Client(timeout=TIMEOUT_S)
    try:
        r = client.post(
            ENDPOINT, headers={"api-subscription-key": key}, data=form, files={"file": (filename, audio)}
        )
    except httpx.HTTPError as e:
        raise SpeechError(f"speech to text did not answer ({type(e).__name__})") from None
    finally:
        if owned:
            client.close()
    if r.status_code != 200:
        raise SpeechError(f"speech to text refused the recording (HTTP {r.status_code})")
    body = r.json()
    if not isinstance(body.get("transcript"), str):
        raise SpeechError("speech to text answered without a transcript")
    return Heard(body["transcript"], body.get("language_code"), body.get("request_id"))
