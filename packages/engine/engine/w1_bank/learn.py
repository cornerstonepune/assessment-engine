"""The bank learns from children's confirmed answers and proposes; a person decides (step 7,
goals/s21-real-difficulty.yaml).

A question's real difficulty is the share of children who got it right, counted only from answers a person has
confirmed (`item_stat`, ring B: rebuilt from nothing each time). A question far easier or far harder than its level
— above `item.flag_high_p` or below `item.flag_low_p`, over at least `item.min_attempts` answers — becomes a
proposal. A person removes it from the bank (`question.remove`: its worksheets are rebuilt) or keeps it. The level
itself is not moved: a level is a rule its questions are measured against (digits, regrouping), and when many of a
level's questions are off, it is the rule people revisit.
"""

from engine.w1_bank import question

LOW, HIGH, MIN = ("item.flag_low_p", 0.20), ("item.flag_high_p", 0.95), ("item.min_attempts", 10)


def _bar(conn, row):
    key, default = row
    found = conn.execute("select value from threshold where key = %s", (key,)).fetchone()
    return float(found["value"]) if found else default


def item_stats(conn) -> int:
    """`item_stat` rebuilt from confirmed answers: each question's attempts, share right, and whether it is far off
    its level. A reading still waiting for a person, or one a later read replaced, is not evidence."""
    low, high, least = _bar(conn, LOW), _bar(conn, HIGH), _bar(conn, MIN)
    conn.execute("delete from item_stat")
    return conn.execute(
        "insert into item_stat (tenant_id, item_id, n, p_correct, flagged_mislevelled)"
        " select r.tenant_id, r.item_id, count(*), avg((r.status = 'correct')::int)::numeric(5, 4),"
        "        count(*) >= %s and (avg((r.status = 'correct')::int) < %s or avg((r.status = 'correct')::int) > %s)"
        " from item_result r join capture c on c.id = r.capture_id"
        " where r.state = 'confirmed' and r.status in ('correct', 'wrong', 'blank') and c.superseded_by is null"
        " group by r.tenant_id, r.item_id",
        (least, low, high),
    ).rowcount


def stat(conn, item_key):
    return conn.execute(
        "select s.* from item_stat s join item i on i.id = s.item_id where i.item_key = %s", (item_key,)
    ).fetchone()


def refresh(conn) -> list[dict]:
    """Rebuild the stats, propose each active question now far off its level that was never proposed that way, and
    → the proposals no one has decided yet, oldest first."""
    item_stats(conn)
    high = _bar(conn, HIGH)
    conn.execute(
        "insert into bank_proposal (tenant_id, kind, subject, direction, evidence)"
        " select i.tenant_id, 'mislevelled', i.item_key, d.direction,"
        "        jsonb_build_object('n', s.n, 'correct', round(s.n * s.p_correct), 'p_correct', s.p_correct,"
        "                           'difficulty', i.difficulty, 'skill_set_code', i.skill_set_code)"
        " from item_stat s join item i on i.id = s.item_id"
        " cross join lateral (select case when s.p_correct > %s then 'easier' else 'harder' end as direction) d"
        " where s.flagged_mislevelled and i.status = 'active' and not exists ("
        "   select 1 from bank_proposal p where p.tenant_id = i.tenant_id and p.kind = 'mislevelled'"
        "   and p.subject = i.item_key and p.direction = d.direction)",
        (high,),
    )
    return conn.execute(
        "select p.id, p.kind, p.subject, p.direction, p.evidence, p.created_at from bank_proposal p"
        " where not exists (select 1 from bank_decision d where d.proposal_id = p.id) order by p.created_at, p.subject"
    ).fetchall()


def decide(conn, proposal_id, verdict, by, note="") -> dict:
    """A person decides a proposal, once: `remove` takes the question out of the bank (its worksheets are rebuilt in
    the same transaction), `keep` leaves it. Raises ValueError for a proposal already decided or a verdict unknown."""
    if verdict not in ("remove", "keep"):
        raise ValueError(f"a proposal is decided remove or keep, not {verdict!r}")
    if not by:
        raise ValueError("a decision names the person deciding")
    p = conn.execute("select * from bank_proposal where id = %s", (proposal_id,)).fetchone()
    if not p:
        raise LookupError(f"no proposal {proposal_id}")
    if conn.execute("select 1 from bank_decision where proposal_id = %s", (proposal_id,)).fetchone():
        raise ValueError("this proposal is already decided")
    if verdict == "remove":
        e = p["evidence"]
        why = note or f"far {p['direction']} than {e['difficulty']}: {e['correct']} of {e['n']} right"
        question.remove(conn, p["subject"], by, why)
    conn.execute(
        "insert into bank_decision (tenant_id, proposal_id, verdict, by, note) values (%s,%s,%s,%s,%s)",
        (p["tenant_id"], proposal_id, verdict, by, note),
    )
    return {"proposal_id": proposal_id, "subject": p["subject"], "verdict": verdict}
