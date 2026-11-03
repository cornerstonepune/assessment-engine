"""The speech-to-text adapter (engine/adapters/speech.py) against a recorded-response stub, never the live service.

The stub's reply has the fields Sarvam's API reference documents (request_id, transcript, language_code), with a
typed transcript of placeholder numbers. The live call on fixtures is manual and not run (goals/m1-01-voice-intake.yaml).
"""

import json

import httpx
import pytest

from engine.adapters import speech
from engine.w3_read import voice_note

REPLY = {
    "request_id": "req-1",
    "transcript": "Activity 4. Above 3, 7. The rest did as expected.",
    "language_code": "en-IN",
}


def stub(status=200, body=REPLY, seen=None):
    def answer(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(request)
        return httpx.Response(status, json=body)

    return httpx.Client(transport=httpx.MockTransport(answer))


def test_one_recording_is_sent_with_the_key_in_its_header_and_its_words_come_back_for_the_reader():
    seen: list[httpx.Request] = []
    heard = speech.transcribe(
        b"RIFF-placeholder", "fx-01.m4a", ["activity", "above"], stub(seen=seen), key="k"
    )
    assert heard == speech.Heard(REPLY["transcript"], "en-IN", "req-1")
    (req,) = seen
    assert str(req.url) == "https://api.sarvam.ai/speech-to-text" and req.method == "POST"
    assert req.headers["api-subscription-key"] == "k"
    body = req.content.decode("latin-1")
    assert 'name="file"; filename="fx-01.m4a"' in body and "RIFF-placeholder" in body
    assert 'name="model"' in body and speech.MODEL in body
    assert json.dumps(["activity", "above"]) in body
    assert voice_note.read(heard.transcript).line("above").numbers == (3, 7)


def test_only_the_recording_and_the_templates_own_words_leave_us():
    seen: list[httpx.Request] = []
    speech.transcribe(b"a", "n.m4a", ["activity"], stub(seen=seen), key="k")
    fields = {
        part.split(b'name="')[1].split(b'"')[0].decode()
        for part in seen[0].content.split(b"Content-Disposition")[1:]
    }
    assert fields == {"file", "model", "language_code", "keyterms"}


def test_the_words_to_listen_for_are_the_templates_headings_within_sarvams_limits():
    headings = [w for s in voice_note.template_from(_rows()).phrases for w in [" ".join(s[0])]]
    terms = speech.keyterms(headings)
    assert 0 < len(terms) <= 50 and all(len(t) <= 64 for t in terms)
    assert speech.keyterms(["x"] * 3 + ["y" * 65]) == ["x"]


def test_no_key_is_an_error_that_says_so():
    with pytest.raises(speech.SpeechError, match="SARVAM_API_KEY is not set"):
        speech.transcribe(b"a", "n.m4a", [], stub(), key="")


def test_a_refusal_says_its_code_and_never_what_was_said(monkeypatch):
    with pytest.raises(speech.SpeechError) as e:
        speech.transcribe(b"a", "n.m4a", [], stub(402, {"error": "Activity 4. Above 3"}), key="k")
    assert "402" in str(e.value) and "Above" not in str(e.value)


def test_a_reply_without_a_transcript_is_an_error():
    with pytest.raises(speech.SpeechError, match="without a transcript"):
        speech.transcribe(b"a", "n.m4a", [], stub(body={"request_id": "r"}), key="k")


def _rows():
    from engine.core import settings

    return settings.seed("voice_template.json", "template")
