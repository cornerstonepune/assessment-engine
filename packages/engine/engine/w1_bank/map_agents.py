"""The curriculum mapping agents: the band read from the database, a proposal for each gap of each activity, its
checks, the validator's verdict, and where it goes (goals/m1-05-mapping-agents.yaml).

Nimish, 2026-11-03: "An agent that has the entire context of what we're trying to build, reads the entire skill map,
and is able to map that. Another validation agent is also needed." The proposer (prompt row
`curriculum_map_propose`) sees the activity, the band's skills in the families people linked to its subject, the
nearest activities people mapped themselves. Code checks every code (`map_check`); a second
model (`curriculum_map_validate`, another model, never shown the proposer's reason) agrees or not. Links between an
objective and a skill are made by code where an activity leaves no doubt (`map_eval.lo_skill_pairs`), not by a model.

Every question to a model goes through one `Ask`: on the box, the adapter (`adapters/llm.py`); in a test or a
recorded run, the replies a file holds. Nothing here writes; `map_ledger` records what this returns.
"""

import hashlib
import json
import re
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast

from engine.adapters import llm
from engine.core import db, settings
from engine.w1_bank import map_offers as offers
from engine.w1_bank.map_check import (  # noqa: F401 — Proposal and Rules are read from here too
    LEVELS,
    Gap,
    Known,
    Proposal,
    Reply,
    Rules,
    asked_levels,
    decide,
    problems,
)
from engine.w1_bank.map_eval import lo_skill_pairs

PROPOSE = "curriculum_map_propose"
VALIDATE = "curriculum_map_validate"
Ask = Callable[
    [str, str, dict[str, object]], Reply
]  # (purpose, the activity or objective asked about, variables)


@dataclass
class Band:
    """One band's curriculum as the agents may see it: what it knows, each activity's gaps and words, and the links
    people made themselves (the gold set and the examples)."""

    known: Known
    gaps: dict[str, Gap]
    words: dict[str, dict[str, str]]
    person_skills: dict[str, frozenset[str]]
    objectives: dict[str, set[str]]
    skills: dict[str, set[str]]
    lo_skills: set[tuple[str, str]]
    names: dict[str, str] = field(default_factory=lambda: {})
    pool: frozenset[str] | None = (
        None  # the activities the proposer may see as examples (the dev set); None: all
    )


def _bad_replies_allowed(conn: db.Conn) -> int:
    """How many replies in a row may break their schema before the run stops (config row k2.drafting)."""
    row = settings.config(conn, "k2.drafting") or {}
    if "stop_after_bad_replies" not in row:
        raise llm.LLMError(
            "the config row k2.drafting is missing: load the settings (engine load --settings)"
        )
    return int(row["stop_after_bad_replies"])


def model_ask(
    conn: db.Conn,
    propose_version: int | None = None,
    validate_version: int | None = None,
    stage: str | None = None,
    say: Callable[[str], None] | None = None,
) -> Ask:
    """The adapter: each question to the prompt row of its purpose (the active one, or the version named), spending
    from `stage` of the campaign that covers these prompts (llm.campaigns). A reply that breaks its schema is one
    activity's loss (`propose` leaves it for a person); replies that keep breaking in a row, counted for each prompt,
    end the run, since the same failure is then being paid for again and again."""
    versions = {PROPOSE: propose_version, VALIDATE: validate_version}
    bad = dict.fromkeys(versions, 0)

    def ask(purpose: str, about: str, variables: dict[str, object]) -> Reply:
        try:
            reply = cast(
                Reply,
                llm.generate(conn, purpose, variables, version=versions[purpose], stage=stage, about=about),
            )
        except llm.LLMSchemaError as e:
            if say:
                say(f"  {about}  {purpose}  REFUSED  {e}")
            bad[purpose] += 1
            if bad[purpose] >= _bad_replies_allowed(conn):
                raise llm.LLMError(
                    f"{bad[purpose]} {purpose} replies in a row broke their schema; stopped, the prompt needs a person"
                ) from e
            raise
        bad[purpose] = 0
        if say:
            say(f"  {about}  {purpose}  accepted")
        return reply

    return ask


def recorded_ask(path: Path) -> Ask:
    """Replies a file holds, {purpose: {code: reply}}, for a test or a recorded run; a question it has no reply to
    fails loudly rather than guess."""
    replies = cast(dict[str, dict[str, Reply]], json.loads(path.read_text()))

    def ask(purpose: str, about: str, variables: dict[str, object]) -> Reply:
        reply = replies.get(purpose, {}).get(about)
        if reply is None:
            raise llm.LLMError(f"no recorded {purpose} reply for {about}")
        return reply

    return ask


def read_band(conn: db.Conn, tenant: db.Id, band: str, hide: frozenset[str] = frozenset()) -> Band:
    """The band from the database. `hide` are held-out activities: their links, their objectives and their part in
    which families fit which subject are taken away, so an eval maps them blind. The band's skills stay whole (those
    with a milestone at the band, and those people linked to any of its activities): they are the registry's list."""
    acts = conn.execute(
        "select code, strand, name, objective, materials, level_0, level_1, level_2, level_3 from activity"
        " where tenant_id = %s and band = %s",
        (tenant, band),
    ).fetchall()
    links = conn.execute(
        "select s.activity_code, s.skill_code, s.source, r.domain from activity_skill s"
        " join activity a on a.tenant_id = s.tenant_id and a.code = s.activity_code"
        " join registry_skill r on r.tenant_id = s.tenant_id and r.code = s.skill_code"
        " where s.tenant_id = %s and a.band = %s",
        (tenant, band),
    ).fetchall()
    objs = conn.execute(
        "select o.activity_code, o.lo_code from activity_objective o"
        " join activity a on a.tenant_id = o.tenant_id and a.code = o.activity_code"
        " where o.tenant_id = %s and a.band = %s",
        (tenant, band),
    ).fetchall()
    strand = {a["code"]: a["strand"] for a in acts}
    skills: dict[str, set[str]] = defaultdict(set)
    person: dict[str, set[str]] = defaultdict(set)
    families: dict[str, set[str]] = defaultdict(set)
    for r in links:
        if r["activity_code"] in hide:
            continue
        skills[r["activity_code"]].add(r["skill_code"])
        if r["source"] == "person":
            person[r["activity_code"]].add(r["skill_code"])
            families[strand[r["activity_code"]]].add(r["domain"])
    objectives: dict[str, set[str]] = defaultdict(set)
    for r in objs:
        if r["activity_code"] not in hide:
            objectives[r["activity_code"]].add(r["lo_code"])
    hidden_los = {r["lo_code"] for r in objs if r["activity_code"] in hide}
    reg = conn.execute(
        "select r.code, r.domain, r.name from registry_skill r where r.tenant_id = %s and (exists (select 1 from"
        " milestone m where m.tenant_id = r.tenant_id and m.skill_code = r.code and m.band = %s) or r.code = any(%s))",
        (tenant, band, sorted({r["skill_code"] for r in links if r["source"] == "person"})),
    ).fetchall()
    los = conn.execute(
        "select code from learning_objective where tenant_id = %s and band = %s", (tenant, band)
    ).fetchall()
    lo_skills = conn.execute(
        "select lo_code, skill_code from learning_objective_skill where tenant_id = %s", (tenant,)
    ).fetchall()
    return Band(
        known=Known(
            skills={r["code"]: r["domain"] for r in reg},
            families={k: frozenset(v) for k, v in families.items()},
            objectives=frozenset(r["code"] for r in los) - hidden_los,
        ),
        gaps={
            a["code"]: Gap(
                activity=a["code"],
                strand=a["strand"],
                skills=frozenset(skills.get(a["code"], set())),
                objectives=frozenset(objectives.get(a["code"], set())),
                levels=frozenset(f for f in LEVELS if (a[f] or "").strip()),
            )
            for a in acts
        },
        words={
            a["code"]: {k: a[k] or "" for k in ("strand", "name", "objective", "materials", *LEVELS)}
            for a in acts
        },
        person_skills={k: frozenset(v) for k, v in person.items()},
        objectives=dict(objectives),
        skills=dict(skills),
        lo_skills={(r["lo_code"], r["skill_code"]) for r in lo_skills},
        names={r["code"]: r["name"] for r in reg},
    )


def kinds_missing(gap: Gap) -> list[str]:
    """The gaps of one activity: no skill, no objective, or no level words at all (a sheet's partly filled levels
    are the educators' own choice and are left as they are)."""
    out = [k for k, have in (("skill", gap.skills), ("objective", gap.objectives)) if not have]
    return out + (["levels"] if not gap.levels else [])


def _words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]{3,}", text.lower())}


def nearest(band: Band, code: str, n: int) -> list[str]:
    """The n activities people mapped whose words are nearest this one's (shared words over all words), from the
    band's example pool only (never a held-out activity), never itself."""
    mine = _words(" ".join(band.words[code].values()))

    def near(other: str) -> float:
        theirs = _words(" ".join(band.words[other].values()))
        return len(mine & theirs) / len(mine | theirs) if mine | theirs else 0.0

    pool = band.person_skills.keys() if band.pool is None else band.person_skills.keys() & band.pool
    return sorted((c for c in pool if c != code), key=lambda c: (-near(c), c))[:n]


def sampled(kind: str, code: str, share: float) -> bool:
    """Whether code sends this proposal to a person as the audit sample: a hash of what it is about, so it is the
    same on every run."""
    return int(hashlib.sha256(f"{kind}:{code}".encode()).hexdigest()[:8], 16) / 0xFFFFFFFF < share


def _context(band: Band, code: str, gaps: list[str], n: int) -> dict[str, object]:
    gap = band.gaps[code]
    fit = band.known.families.get(gap.strand, frozenset())
    return {
        "activity": {"code": code, **band.words[code]},
        "gaps": gaps,
        "skills": [
            f"{c} {band.names.get(c, '')}" for c, fam in sorted(band.known.skills.items()) if fam in fit
        ],
        "examples": [
            {
                **band.words[c],
                "skills": sorted(band.person_skills[c]),
                "objectives": sorted(band.objectives.get(c, [])),
            }
            for c in nearest(band, code, n)
        ],
    }


def _split(kind: str, reply: Reply, gap: Gap) -> Reply:
    if kind == "skill":
        return {"skills": reply.get("skills") or []}
    if kind == "objective":
        return {
            "objective_code": reply.get("objective_code") or "",
            "objective_text": reply.get("objective_text") or "",
        }
    return {"levels": asked_levels(reply.get("levels") or {}, gap)}


def _checked(
    band: Band,
    kind: str,
    code: str,
    part: Reply,
    confidence: float,
    rules: Rules,
    ask: Ask,
    proposer: str,
    gap: Gap,
) -> Proposal:
    found = problems(kind, part, gap, band.known)
    verdict, why = "", ""
    if not found and rules.use_checker:
        listed = cast(list[str], part.get("skills") or [])
        try:
            v = ask(
                VALIDATE,
                code,
                {
                    "activity": {"code": code, **band.words.get(code, {})},
                    "kind": kind,
                    "proposal": part,
                    "skills": [f"{c} {band.names.get(c, '')}" for c in listed],
                },
            )
            verdict, why = str(v.get("verdict", "")), str(v.get("why", ""))
        except llm.LLMSchemaError:
            why = "the checker's reply broke its schema, so this proposal is not checked"
    audit = sampled(kind, code, rules.audit_share)
    status = decide(
        kind,
        found,
        verdict,
        confidence,
        min_confidence=rules.bar(kind),
        sampled=audit,
        checker=rules.use_checker,
        new_words=bool(part.get("objective_text")),
        none=kind in ("skill", "lo_skill") and not part.get("skills"),
        kind_stopped=kind in rules.stopped,
    )
    reason = "; ".join(found) or ("audit sample" if audit and status == "needs_person" else why)
    return Proposal(
        kind, code, part, confidence, proposer, VALIDATE if verdict else "", found, verdict, status, reason
    )


def _broken(kind: str, code: str) -> Proposal:
    """What a proposer reply that broke its schema leaves: nothing proposed, and the reason in words."""
    why = "the proposer's reply broke its schema, so nothing is proposed for this activity"
    return Proposal(
        kind=kind,
        subject_code=code,
        proposal={},
        confidence=0.0,
        proposer=PROPOSE,
        validator="",
        problems=[why],
        verdict="",
        status="rejected",
        reason=why,
    )


def propose(
    band: Band,
    codes: list[str],
    ask: Ask,
    rules: Rules,
    asked: frozenset[tuple[str, str]] = frozenset(),
) -> list[Proposal]:
    """A decided proposal for each gap of each activity named: the proposer asked once per activity, each part
    checked by code, the validator asked where code found nothing wrong."""
    out: list[Proposal] = []
    for code in codes:
        gaps = kinds_missing(band.gaps[code])
        if not gaps:
            continue
        context = _context(band, code, gaps, rules.examples)
        try:
            reply = ask(PROPOSE, code, context)
        except llm.LLMSchemaError:
            out += [
                _broken(kind, code) for kind in gaps
            ]  # one activity left for a person; the next is still asked
            continue
        confidence = float(cast(float, reply.get("confidence", 0.0)))
        for kind in gaps:
            out += offers.split(
                _checked(
                    band,
                    kind,
                    code,
                    _split(kind, reply, band.gaps[code]),
                    confidence,
                    rules,
                    ask,
                    PROPOSE,
                    band.gaps[code],
                ),
                offers.shown_in(context),
                rules,
                asked,
            )
    return out


def propose_lo_skills(
    band: Band, ask: Ask, rules: Rules, already: frozenset[tuple[str, str]] = frozenset()
) -> list[Proposal]:
    """Objective → skill links made by code where an activity leaves no doubt, each still read by the validator."""
    out: list[Proposal] = []
    for (lo, sk), activity in sorted(lo_skill_pairs(band.objectives, band.skills).items()):
        if (lo, sk) in band.lo_skills or (lo, sk) in already:
            continue
        mine = frozenset(s for o, s in band.lo_skills if o == lo)
        gap = Gap(
            activity=lo,
            strand=band.gaps[activity].strand,
            skills=mine,
            objectives=frozenset(),
            levels=frozenset(),
        )
        out.append(
            _checked(
                band, "lo_skill", lo, {"skills": [sk], "shown_by": activity}, 1.0, rules, ask, "code", gap
            )
        )
    return out
