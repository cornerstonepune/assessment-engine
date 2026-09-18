"""The auth dependency is the whole boundary between an unauthenticated caller and the database.
A false negative (rejecting a valid key) is merely annoying; a false positive is the actual risk
— so the case worth the most attention is what happens when ENGINE_KEY itself is unset, which
must refuse everything rather than let an unset header match an unset secret.
"""
import pytest
from fastapi import HTTPException

from engine.api.deps import require_engine_key


def test_the_correct_key_passes(monkeypatch):
    monkeypatch.setenv("ENGINE_KEY", "secret123")
    require_engine_key(x_engine_key="secret123")  # does not raise


def test_a_wrong_key_is_refused_with_401(monkeypatch):
    monkeypatch.setenv("ENGINE_KEY", "secret123")
    with pytest.raises(HTTPException) as exc:
        require_engine_key(x_engine_key="wrong")
    assert exc.value.status_code == 401


def test_no_key_at_all_is_refused_with_401(monkeypatch):
    monkeypatch.setenv("ENGINE_KEY", "secret123")
    with pytest.raises(HTTPException) as exc:
        require_engine_key(x_engine_key=None)
    assert exc.value.status_code == 401


def test_an_unconfigured_engine_key_refuses_everything_rather_than_accepting_anything(monkeypatch):
    """The dangerous failure mode: ENGINE_KEY unset, a header also unset, and an == check that
    would silently pass None == None. This must refuse loudly (500, misconfigured) instead."""
    monkeypatch.delenv("ENGINE_KEY", raising=False)
    with pytest.raises(HTTPException) as exc:
        require_engine_key(x_engine_key=None)
    assert exc.value.status_code == 500


def test_an_empty_string_key_never_matches_an_unconfigured_secret(monkeypatch):
    monkeypatch.delenv("ENGINE_KEY", raising=False)
    with pytest.raises(HTTPException) as exc:
        require_engine_key(x_engine_key="")
    assert exc.value.status_code == 500


def test_an_empty_configured_key_also_refuses_everything(monkeypatch):
    """An ENGINE_KEY set to the empty string is not a valid configuration either — it must not
    become a secret an empty header can match."""
    monkeypatch.setenv("ENGINE_KEY", "")
    with pytest.raises(HTTPException) as exc:
        require_engine_key(x_engine_key="")
    assert exc.value.status_code == 500
