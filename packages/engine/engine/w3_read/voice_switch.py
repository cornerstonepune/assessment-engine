"""The two K2 voice-note switches, turned by a command that names who turned them (task M1-04): never by hand on live.

`voice.screens_enabled` shows the K2 educator What needs doing's K2 rows, the form and Confirm. `voice.recording_enabled`
lets her record and hear a note back, on top of the screens; it is not turned on without the reference of Sarvam's
written confirmation of "No retention" (D-065). Each turn is written to `access_log` under the signer's staff id (as a
people load is signed, `core/signer.py`), with the reference when there is one; nothing prints an email.
"""

from engine.core import db, settings, signer

KEYS = {"screens": "voice.screens_enabled", "recording": "voice.recording_enabled"}
NO_REFERENCE = (
    "recording stays off: give --retention-ref, the reference of Sarvam's written confirmation that the school's"
    " workspace keeps no recording (D-065)"
)


def switch(conn: db.Conn, which: str, on: bool, by: str, retention_ref: str | None = None) -> str:
    """Turn one switch, signed by `by` (the email they sign in with) → what changed, in words with no email."""
    key = KEYS.get(which)
    if key is None:
        raise ValueError(f"no such switch: say {' or '.join(KEYS)}")
    ref = (retention_ref or "").strip()
    if which == "recording" and on and not ref:
        raise ValueError(NO_REFERENCE)
    who = signer.resolve(conn, by)
    was = settings.config(conn, key, False) is True
    conn.execute(
        "insert into config (tenant_id, key, value, description) select id, %s, %s::jsonb, %s from tenant"
        " on conflict (tenant_id, key) do update set value = excluded.value",
        (key, "true" if on else "false", f"set by `engine read voice switch {which}`"),
    )
    action = f"{key} {'on' if on else 'off'}" + (f", retention-ref: {ref}" if ref and on else "")
    conn.execute(
        "insert into access_log (tenant_id, actor, action, occurred_at) select id, %s, %s, clock_timestamp() from tenant",
        (who, action),
    )
    return f"{key}: {'on' if on else 'off'} (was {'on' if was else 'off'}); logged"
