"""One sweep over every invariant the rows must satisfy. `engine audit`.

Written because bugs were being found one at a time, by whichever test happened to touch them: a
spec claiming a mistake the engine cannot mark, a curated code unreachable in its own bands, two
prompt versions active at once. Each was fixed, and each left the same question unanswered — what
else is wrong that nothing looks at?

Every invariant here is a named property of the whole database, checked in one command. A violation
prints the rows that break it. Adding a new class of bug means adding an invariant here, not another
test that happens to notice it. What this file does NOT check is, by definition, what we do not know.
"""

from engine import bank, cases, db, labels, loaders, spec
from engine.assess import bands, verify
from engine.assess import misconceptions as M

PREDICTOR_CODES = {c for table in (M.ADD_PREDICTORS, M.SUB_PREDICTORS, M.MULTI_PREDICTORS) for c in table}


def _skill_sets(conn):
    return conn.execute(
        "select code, rung_code, status, formats, difficulty, misconception_codes as curated"
        " from skill_set order by code"
    ).fetchall()


def every_rung_has_a_spec(conn):
    return [
        r["code"]
        for r in conn.execute(
            "select code from rung r where not exists"
            " (select 1 from skill_set s where s.rung_code = r.code) order by code"
        ).fetchall()
    ]


def every_spec_is_ratified(conn):
    return [f"{r['code']} is {r['status']}" for r in _skill_sets(conn) if r["status"] != "ratified"]


def no_spec_claims_a_mistake_its_own_numbers_cannot_produce(conn):
    """A curated code a predictor *can* compute must be reachable in that set's own bands. If it is
    not, the spec promises a diagnosis no marker can deliver — `ADDSUB.2D.NOREG` claiming
    'takes the smaller digit' where no exchange happens, which produces the right answer."""
    out = []
    for r in _skill_sets(conn):
        reachable = {c for codes in spec.known_misconceptions(conn, r["code"]).values() for c in codes}
        if not reachable:
            continue  # no numbers to sample: nothing claimed, nothing to check
        unreachable = (set(r["curated"]) & PREDICTOR_CODES) - reachable
        if unreachable:
            out.append(f"{r['code']} claims {', '.join(sorted(unreachable))}")
    return out


def every_band_can_produce_a_question(conn):
    """A rule whose numbers cannot be sampled and whose format has no generator is a band the bank
    can never fill — invisible until a fill runs and returns nothing."""
    return [
        f"{r['code']} {d}: nothing can make this rule ({band.get('check') or {}})"
        for r in _skill_sets(conn)
        for d, band in r["difficulty"].items()
        if not bands.makeable(band.get("check") or {})
    ]


def every_key_a_level_sets_is_one_its_generator_reads(conn):
    """A level's rule is a promise about the questions it prints. A key no generator reads is a promise
    nobody keeps — ADDSUB.2D.NOREG's `order: shorter_first` printed longer-first sums, and the four
    WORD.BUDGET levels asked for different costs and budgets and printed the same problem (step 8f)."""
    matches = cases.matches(conn)
    out = []
    for r in _skill_sets(conn):
        for d, band in r["difficulty"].items():
            check = band.get("check") or {}
            kinds = {
                f
                for c in check.get("cases", [])
                for alt in _alternatives(matches.get(c, {}))
                for f in _fmts(alt)
            }
            unread = bands.unread_keys(check, kinds)
            if unread:
                out.append(f"{r['code']} {d}: {', '.join(unread)} — nothing reads it")
    return out


def every_case_a_level_names_is_a_row(conn):
    known = set(cases.matches(conn))
    return [
        f"{r['code']} {d}: {c}"
        for r in _skill_sets(conn)
        for d, band in r["difficulty"].items()
        for c in (band.get("check") or {}).get("cases", [])
        if c not in known
    ]


def _alternatives(match):
    return match if isinstance(match, list) else [match]


def _fmts(alt):
    f = alt.get("fmt")
    return f if isinstance(f, list) else [f] if f else []


def every_format_a_spec_lists_can_be_made(conn):
    known = set(verify.FORMATS) | set(bands.NATIVE_GENERATORS)
    return [f"{r['code']}: {f}" for r in _skill_sets(conn) for f in r["formats"] if f not in known]


def every_answer_lookup_code_is_computed_somewhere(conn):
    """A mistake the vocabulary says is "identifiable from the answer alone" must have something that
    computes that answer — a predictor, or a generator that names it on the items it builds.
    Otherwise the promise is empty: the marker has no number to compare against."""
    claimed = {
        r["code"]
        for r in conn.execute(
            "select distinct code from misconception where detectable_by = 'answer_lookup'"
        ).fetchall()
    }
    emitted = set(M.PREDICTED)
    for r in _skill_sets(conn):
        for codes in spec.known_misconceptions(conn, r["code"], 10).values():
            emitted |= set(codes)
    return sorted(claimed - emitted)


def every_misconception_a_stored_item_names_exists(conn):
    return [
        f"{r['code']} on {r['n']} items"
        for r in conn.execute(
            "select code, count(*) as n from ("
            "  select jsonb_object_keys(r -> 'misconceptions') as code"
            "  from item i, jsonb_array_elements(i.responses) r"
            "  where i.status = 'active' and jsonb_typeof(r -> 'misconceptions') = 'object') x"
            " where not exists (select 1 from misconception v where v.code = x.code)"
            " group by code order by code"
        ).fetchall()
    ]


def exactly_one_prompt_version_is_active_per_purpose(conn):
    return [
        f"{r['purpose']}: {r['n']} active"
        for r in conn.execute(
            "select purpose, count(*) as n from prompt where active group by purpose"
            " having count(*) <> 1 order by purpose"
        ).fetchall()
    ]


def no_wrong_or_blank_stands_on_the_engines_reading_alone(conn):
    """ADR 0029: a wrong or a blank counts once a person has said what the child wrote, or signed the
    paper off. Anything else is the reader's word against a child's record."""
    n = conn.execute(
        "select count(*) as n from item_result r join capture c on c.id = r.capture_id"
        " where c.superseded_by is null and r.state = 'candidate' and r.status in ('wrong', 'blank')"
        " and not exists (select 1 from read_correction rc where rc.item_result_id = r.id)"
    ).fetchone()["n"]
    return [f"{n} wrong or blank answers stand on the engine's reading alone"] if n else []


def every_generated_item_says_what_made_it(conn):
    n = conn.execute(
        "select count(*) as n from item where status = 'active' and source = 'generated'"
        " and (skill_set_version is null or generator is null)"
    ).fetchone()["n"]
    return [f"{n} generated items carry no version or generator"] if n else []


def every_unit_meets_its_target(conn):
    return [
        f"{r['code']} {r['difficulty']}: {r['n']} of {r['target']}"
        for r in bank.coverage(conn)
        if r["n"] < r["target"]
    ]


def every_stored_item_still_satisfies_its_band(conn):
    return list(bank.recheck(conn))


def no_question_carries_a_skill_it_does_not_use(conn):
    """ADR 0023: a question's skills are the ones it uses, read from the question — never its rung's."""
    return labels.mislabelled(conn)


def what_a_mistake_charges_is_approved(conn):
    """The (kind, mistake) → skill table was drafted by the engine; a person approves the table itself,
    so a table changed after it was approved is not approved (step 8b, as the gold was)."""
    rows = {
        r["key"]: r["value"]
        for r in conn.execute("select key, value from config where key like 'skills.charges_by_kind%'")
    }
    approved = rows.get("skills.charges_by_kind.approved") or {}
    if approved.get("table") == rows.get("skills.charges_by_kind") and approved.get("by"):
        return []
    return ["the table of what a mistake charges on each kind of question waits for one approval"]


def referential_codes_all_resolve(_conn):
    return [f"{label}: {', '.join(codes)}" for label, codes in loaders.orphans().items() if codes]


# Invariants a person closes, not code: an approval on the Skill Map. `engine audit` counts them like
# any other; the test suite does not, because a suite proves the code and a click is not code.
AWAITS_A_PERSON = {"every spec is ratified", "what a mistake charges is approved"}

# Ordered cheapest first, so a run that fails early has still said something useful.
INVARIANTS = [
    ("every rung has a spec", every_rung_has_a_spec),
    ("every spec is ratified", every_spec_is_ratified),
    ("what a mistake charges is approved", what_a_mistake_charges_is_approved),
    ("every code a spec references resolves", referential_codes_all_resolve),
    ("exactly one prompt version active per purpose", exactly_one_prompt_version_is_active_per_purpose),
    (
        "no wrong or blank answer stands on the engine's reading alone",
        no_wrong_or_blank_stands_on_the_engines_reading_alone,
    ),
    ("every format a spec lists can be made", every_format_a_spec_lists_can_be_made),
    ("every key a level sets is one its generator reads", every_key_a_level_sets_is_one_its_generator_reads),
    ("every case a level names is a row", every_case_a_level_names_is_a_row),
    ("every band can produce a question", every_band_can_produce_a_question),
    (
        "no spec claims a mistake its own numbers cannot produce",
        no_spec_claims_a_mistake_its_own_numbers_cannot_produce,
    ),
    ("every misconception a stored item names exists", every_misconception_a_stored_item_names_exists),
    ("every answer-lookup code is computed somewhere", every_answer_lookup_code_is_computed_somewhere),
    ("every generated item says what made it", every_generated_item_says_what_made_it),
    ("no question carries a skill it does not use", no_question_carries_a_skill_it_does_not_use),
    ("every unit meets its target", every_unit_meets_its_target),
    ("every stored item still satisfies its band", every_stored_item_still_satisfies_its_band),
]


def run(conn=None):
    """[(invariant, [violations])] in order. A caller with no connection gets its own."""
    if conn is not None:
        return [(name, fn(conn)) for name, fn in INVARIANTS]
    with db.connect() as own:
        return [(name, fn(own)) for name, fn in INVARIANTS]
