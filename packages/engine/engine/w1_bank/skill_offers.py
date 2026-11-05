"""Skill proposals waiting for a person, and their answer (goals/m1-12c-skill-offers.yaml, task M1-12c).

A skill the proposer was not shown in an example is a `skill_offer`; a skill proposal under the confidence bar waits too.
Both are listed here for the screen, and answered: yes adds that proposal's skills as the machine's links (naming the
proposal, so any can be reverted), no closes it. Only that one proposal is made or turned down; anything else waiting to be
applied is applied by `engine curriculum apply`, as before.
"""

import uuid

from engine.core import db
from engine.w1_bank import map_ledger

KINDS = {"skill": "skill", "skill_offer": "offer"}


def waiting(conn: db.Conn, tenant: db.Id) -> list[dict]:
    """The skill proposals waiting for a person, by activity: each with the activity, the skills, what was proposed
    beside them, the model's confidence and why it waits."""
    rows = [
        p
        for p in map_ledger.standing(conn, tenant, "needs_person")
        if p["kind"] in KINDS and p["proposal"].get("skills")
    ]
    names = {
        r["code"]: r["name"]
        for r in conn.execute(
            "select code, name from registry_skill where tenant_id = %s", (tenant,)
        ).fetchall()
    }
    acts = {
        r["code"]: r
        for r in conn.execute(
            "select code, name, strand from activity where tenant_id = %s and code = any(%s)",
            (tenant, sorted({p["subject_code"] for p in rows})),
        ).fetchall()
    }

    def skills(codes: list[str]) -> list[dict]:
        return [{"code": c, "name": names.get(c, "")} for c in codes]

    out = [
        {
            "id": str(p["id"]),
            "kind": KINDS[p["kind"]],
            "activity": {
                "code": p["subject_code"],
                "name": acts[p["subject_code"]]["name"] if p["subject_code"] in acts else "",
                "section": acts[p["subject_code"]]["strand"] if p["subject_code"] in acts else "",
            },
            "skills": skills(p["proposal"]["skills"]),
            "also": skills(p["proposal"].get("with") or []),
            "confidence": float(p["confidence"]) if p["confidence"] is not None else 0.0,
            "reason": p["reason"],
        }
        for p in rows
    ]
    return sorted(out, key=lambda w: (w["activity"]["code"], w["kind"] != "skill", w["skills"][0]["code"]))


def answer(conn: db.Conn, tenant: db.Id, staff: db.Id, proposal: str, yes: bool, why: str) -> None:
    """A person's yes or no to one waiting proposal; a yes makes its links."""
    if not any(w["id"] == str(proposal) for w in waiting(conn, tenant)):
        raise ValueError(f"{proposal} is not waiting for a person")
    pid = uuid.UUID(str(proposal))
    map_ledger.settle(conn, tenant, pid, yes, staff, why)
    if yes:
        map_ledger.apply(conn, tenant, staff, True, only=pid)
