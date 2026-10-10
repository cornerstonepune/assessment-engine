"""A story is its numbers, its shape and its operations (goals/as2-a-story-is-its-shape.yaml, ADR 0053).

Its key said only its numbers, so on a level of small numbers the story cases listed first took every pair and the ones
after them were never held: filled whole, SUB.1D1D's Advance held no W02, W03 or W11, and ADD.1D1D's no W06. Its shape
was read from its words, so a story an educator reworded lost it at the next relabel, and the refill retired it."""

import dataclasses
import json
import os
import pathlib
import random
from collections import Counter, defaultdict

import psycopg
import pytest

from engine.assess import draw, items, tags, taxonomy, verify
from engine.assess import misconceptions as M
from engine.assess import words as W
from engine.core import db
from engine.w1_bank import bank, inventory, labels, question, story_keys
from tests.rows import a_child, tenant

SEED = pathlib.Path(__file__).resolve().parents[3] / "supabase" / "seed"
SETS = {s["code"]: s for s in json.loads((SEED / "skill_sets.json").read_text())["skill_sets"]}
CASES = {c["code"]: c for c in json.loads((SEED / "taxonomy_cases.json").read_text())["taxonomy_cases"]}
CONFIG = {r["key"]: int(r["value"]) for r in json.loads((SEED / "config.json").read_text())["config"]
          if r["key"] in ("bank.class_size", "assemble.spares_per_difficulty", "assemble.items_per_sheet")}  # fmt: skip


def _target(level):
    """What `bank refill` fills a level to (`inventory.coverage`): its own floor, else a class's week."""
    need = (CONFIG["bank.class_size"] + CONFIG["assemble.spares_per_difficulty"]) * CONFIG[
        "assemble.items_per_sheet"
    ]
    return int(level.get("min_items") or need)


def _key(template, spec):
    """The key worked out from what a story is, in the order the bank writes it — not read back from the code."""
    return items._id(template, spec)


@pytest.mark.parametrize("code", ["SUB.1D1D", "ADD.1D1D"])
def test_a_level_filled_whole_holds_every_story_shape_it_lists(code):
    """Filled whole, as `bank refill` fills it and a scenario asks for it: every case the level lists is held, each
    question once. Keyed by their numbers alone, the seven subtraction stories shared 36 pairs and the four addition
    stories 72, and the shapes listed last were never held."""
    level = SETS[code]["difficulty"]["Advance"]
    check, n = level["check"], _target(level)
    matches = {c: taxonomy.within(CASES[c]["match"], check.get("within")) for c in check["cases"]}
    for seed in range(3):
        got = draw.level(random.Random(seed), check, matches, SETS[code]["rung_code"], n)
        assert len(got) == n and len({it.item_id for _, it in got}) == n, (code, seed, len(got))
        held = Counter(
            c
            for _, it in got
            for c in check["cases"]
            if taxonomy.matches(matches[c], it.fmt, tags.derive(it))
        )
        assert not [c for c in check["cases"] if not held[c]], (code, seed, dict(held))


def test_a_story_is_its_numbers_its_shape_and_its_operations():
    """One numbers pair in two shapes is two questions; two wordings of one shape are one. A two-step story carries its
    operations too: two templates of one shape whose answers differ are two questions."""
    rng, keys = random.Random(3), defaultdict(set)
    one_step = [t for t in W.templates("word_1step") if t["op"] in "+-" and not t.get("table")]
    for shape in sorted({t["structure"] for t in one_step}):
        for _ in range(30):
            it = W.word_1step(rng, "R1", "Application", 1, regroups=(0,), structure=shape)
            a, b, op = it.spec["a"], it.spec["b"], it.spec["op"]
            assert it.spec == {"a": a, "b": b, "op": op, "structure": shape}
            assert it.item_id == _key("WP1", {"a": a, "b": b, "op": op, "structure": shape})
            keys[(a, b, op)].add((shape, it.item_id))
    shared = [ks for ks in keys.values() if len({s for s, _ in ks}) > 1]
    assert shared, "no numbers pair was drawn in two shapes"
    assert all(len({k for _, k in ks}) == len({s for s, _ in ks}) for ks in shared)
    for shape in ("UNKNOWN_FIRST", "EXTRA_INFORMATION", "CONSTRAINT", "SUB_SUB"):
        for _ in range(12):
            it = W.word_2step(rng, "R12", "Application", 3, structure=shape)
            tpl = W.template_of(it.stem)
            assert tpl and tpl["structure"] == shape
            ops = list(dict.fromkeys(tpl["op"]))
            spec = {"a": it.spec["a"], "b": it.spec["b"], "c": it.spec["c"], "structure": shape, "ops": ops}
            assert it.spec == spec and it.item_id == _key("WP2", spec)


def test_no_two_templates_share_a_key_and_compute_differently():
    """A story's key is everything about its template but its words, so two templates that key one set of numbers alike
    must give it one answer. UNKNOWN_FIRST, EXTRA_INFORMATION and CONSTRAINT each hold two arithmetics; their
    operations tell them apart. A template added later that breaks this fails here, before it can lose a question."""
    nums, answers = {"a": 90, "b": 30, "c": 12}, defaultdict(set)
    for t in W.templates("word_1step") + W.templates("word_2step"):
        if t["fmt"] == "word_1step":
            spec, code, answer = W.story_spec(t, a=nums["a"], b=nums["b"]), "WP1", M.compute(t["op"], 90, 30)
        else:
            spec, code = W.story_spec(t, **nums), "WP2"
            answer = W.evaluate(t["answer"], nums, divide=t.get("divide", 1))
        answers[_key(code, spec)].add(answer)
    assert all(len(v) == 1 for v in answers.values()), {k: v for k, v in answers.items() if len(v) > 1}
    two_step = {_key("WP2", W.story_spec(t, **nums)) for t in W.templates("word_2step")}
    assert len(two_step) == len({(t["structure"], t["op"]) for t in W.templates("word_2step")})


def test_both_ways_into_the_bank_key_a_story_alike():
    """A story the sampler writes and the bank checks (`verify.to_item`) is keyed as the drawer keys the same story. A
    story whose words no template wrote names no shape, and is keyed by its numbers, as it always was."""
    rng = random.Random(8)
    for t in [t for t in W.templates("word_1step") if t["op"] in "+-" and not t.get("table")]:
        it = W.word_1step(rng, "R5", "Application", 2, structure=t["structure"], op=t["op"])
        c = {
            "format": "word_1step",
            "op": it.spec["op"],
            "a": it.spec["a"],
            "b": it.spec["b"],
            "answer": int(it.responses[0].answer),
            "stem": it.stem,
            "misconceptions": [],
        }
        assert verify.to_item(c, "R5").item_id == it.item_id, (t["structure"], it.stem)
    shopkeeper = "A shopkeeper had 353 mangoes and sold 26 of them. How many are left?"
    c = {
        "format": "word_1step",
        "op": "-",
        "a": 353,
        "b": 26,
        "answer": 327,
        "stem": shopkeeper,
        "misconceptions": [],
    }
    assert verify.to_item(c, "R8").item_id == _key("WP1", {"a": 353, "b": 26, "op": "-"})


@pytest.fixture
def conn():
    if not os.getenv("DATABASE_URL"):
        pytest.skip("needs DATABASE_URL (see .env.example)")
    with db.connect() as c:
        yield c
        c.rollback()


def _fresh(conn, make, as_it_was=True):
    """A story the bank does not hold yet, under the key it has now and, `as_it_was`, the key it had before."""
    for _ in range(200):
        it = make()
        old = {k: v for k, v in it.spec.items() if k not in ("structure", "ops")}
        was = dataclasses.replace(it, item_id=_key(it.template, old), spec=old)
        keys = [it.item_id, was.item_id] if as_it_was else [it.item_id]
        if not conn.execute("select 1 from item where item_key = any(%s)", (keys,)).fetchone():
            return it, was
    raise AssertionError("every story drawn is in the bank already")


RUNG = SETS["SUB.2D2D"]["rung_code"]  # where a stored story sits does not change how it is keyed


def _stored(conn, it, retired=False, code="SUB.2D2D"):
    assert bank._insert(conn, tenant(conn), it, code, "Advance")
    row = conn.execute("select id from item where item_key = %s", (it.item_id,)).fetchone()
    if retired:
        conn.execute(
            "insert into item_feedback (tenant_id, item_id, actor, verdict, note) values (%s,%s,'test','retire','')",
            (tenant(conn), row["id"]),
        )
    return row["id"]


def _row(conn, item_id):
    return conn.execute(
        "select item_key, spec, stem, responses, status, tags from item where id = %s", (item_id,)
    ).fetchone()


def test_a_stored_story_is_keyed_again_and_what_names_it_follows(conn):
    """Every story stored before its shape was part of it is keyed as the bank keys it now, once: its words, numbers
    and answer unchanged, the review and gold finding that name it following it, the proposal that named it (in an
    append-only ledger) finding it by the key it had, a retired story still retired. A rewording keeps its own key and takes the shape of the story it rewords, so a relabel no longer loses
    it. A story whose words no template wrote keeps its key. One the bank already holds under its new key is the
    same question twice, and the old row is retired. A second run changes nothing."""
    rng = random.Random(11)
    one = lambda shape: lambda: W.word_1step(rng, RUNG, "Application", 2, structure=shape)  # noqa: E731
    take_away, start_unknown = _fresh(conn, one("SEPARATE_RESULT")), _fresh(conn, one("JOIN_START"))
    retired, reworded = _fresh(conn, one("COMPARE_DIFFERENCE")), _fresh(conn, one("PPW_PART"))
    two_step = _fresh(conn, lambda: W.word_2step(rng, RUNG, "Application", 3, structure="UNKNOWN_FIRST"))
    twice = _fresh(conn, one("JOIN_CHANGE"))
    ids = {
        "take_away": _stored(conn, take_away[1]),
        "start_unknown": _stored(conn, start_unknown[1]),
        "retired": _stored(conn, retired[1], retired=True),
        "reworded": _stored(conn, reworded[1]),
        "two_step": _stored(conn, two_step[1]),
        "twice_new": _stored(conn, twice[0]),
        "twice_old": _stored(conn, twice[1]),
    }
    shopkeeper = items.item(
        "WP1",
        RUNG,
        "Application",
        "word_1step",
        "A shopkeeper had 353 mangoes and sold 26 of them. How many are left?",
        {"a": 353, "b": 26, "op": "-"},
        [items.Response("ans", "digits", "327", cells=4, misconceptions={})],
    )
    if not conn.execute("select 1 from item where item_key = %s", (shopkeeper.item_id,)).fetchone():
        ids["unwritten"] = _stored(conn, shopkeeper)
    unwritten_key = shopkeeper.item_id
    new = question.correct(
        conn, reworded[1].item_id, "Read carefully. " + reworded[1].stem, "test", "clearer"
    )
    ids["rewording"] = conn.execute("select id from item where item_key = %s", (new["item_key"],)).fetchone()[
        "id"
    ]
    old_key, t = take_away[1].item_id, tenant(conn)
    conn.execute(
        "insert into item_review (tenant_id, reviewer, skill_set_code, difficulty, ref, verdict)"
        " values (%s, 'language_review', 'SUB.2D2D', 'Advance', %s, 'pass')",
        (t, old_key),
    )
    conn.execute(
        "insert into gold_finding (tenant_id, child_id, verdict, skill_code, item_key, words, source)"
        " values (%s, %s, 'faulty', 'NUM.OPS.02', %s, 'a test finding', 'test')",
        (t, a_child(conn), old_key),
    )
    conn.execute(
        "insert into bank_proposal (tenant_id, kind, subject, direction, evidence)"
        " values (%s, 'mislevelled', %s, 'easier', '{}')",
        (t, old_key),
    )
    before = {name: _row(conn, i) for name, i in ids.items()}

    out = story_keys.rekey(conn)

    for name, (now, _) in {
        "take_away": take_away,
        "start_unknown": start_unknown,
        "two_step": two_step,
    }.items():
        row = _row(conn, ids[name])
        assert (row["item_key"], row["spec"]) == (now.item_id, now.spec), name
        assert (row["stem"], row["responses"], row["status"]) == (
            before[name]["stem"],
            before[name]["responses"],
            "active",
        )
    assert (_row(conn, ids["retired"])["item_key"], _row(conn, ids["retired"])["status"]) == (
        retired[0].item_id,
        "retired",
    )
    assert _row(conn, ids["reworded"])["item_key"] == reworded[0].item_id
    rewording = _row(conn, ids["rewording"])
    assert rewording["item_key"] == new["item_key"] and rewording["spec"]["structure"] == "PPW_PART"
    assert (_row(conn, ids["twice_old"])["item_key"], _row(conn, ids["twice_old"])["status"]) == (
        twice[1].item_id,
        "retired",
    )
    assert _row(conn, ids["twice_new"]) == before["twice_new"]
    assert conn.execute("select 1 from item where item_key = %s", (unwritten_key,)).fetchone()
    for table, column in story_keys.NAMED_BY_KEY:
        assert (
            conn.execute(f"select count(*) as n from {table} where {column} = %s", (old_key,)).fetchone()["n"]
            == 0
        )
        assert (
            conn.execute(
                f"select count(*) as n from {table} where {column} = %s", (take_away[0].item_id,)
            ).fetchone()["n"]
            == 1
        ), table
    assert out["keyed"] >= 5 and out["duplicates"] >= 1 and out["reworded"] >= 1 and out["unwritten"] >= 1
    assert all(out["followed"][table] >= 1 for table, _ in story_keys.NAMED_BY_KEY)
    # a proposal is in an append-only ledger: it keeps the key it named, and that key still leads to its question
    assert (
        conn.execute("select count(*) as n from bank_proposal where subject = %s", (old_key,)).fetchone()["n"]
        == 1
    )
    assert inventory.current_key(conn, old_key) == take_away[0].item_id
    assert question._row(conn, old_key)["id"] == ids["take_away"]

    labels.relabel(conn)
    rewording = _row(conn, ids["rewording"])
    assert rewording["tags"].get("structure") == "PPW_PART" and rewording["status"] == "active"

    again = story_keys.rekey(conn)
    assert (again["keyed"], again["duplicates"], again["reworded"]) == (0, 0, 0)
    assert sum(again["followed"].values()) == 0


def test_bank_recheck_still_rebuilds_a_story_and_names_one_changed_by_hand(conn):
    """`bank recheck` rebuilds every question from its spec and names any that disagree. A story's spec now holds its
    shape, which the recheck took for a field it could not rebuild: every one-step story would have left the audit."""
    rng, code = random.Random(4), "SUB.1D1D"
    rung = SETS[code]["rung_code"]
    make = lambda: W.word_1step(rng, rung, "Application", 1, regroups=(0,), structure="SEPARATE_RESULT")  # noqa: E731
    it, _ = _fresh(conn, make, as_it_was=False)
    _stored(conn, it, code=code)
    assert it.item_id not in inventory.recheck(conn)
    conn.execute(
        "update item set responses = jsonb_set(responses::jsonb, '{0,answer}', '\"99\"')::json where item_key = %s",
        (it.item_id,),
    )
    assert it.item_id in inventory.recheck(conn)


def test_a_question_whose_key_never_changed_can_be_deleted_and_one_whose_key_did_cannot(conn):
    """The key-change ledger is append-only, and must not make every question undeletable: a cascade from a deleted
    question into it is a DELETE the ledger refuses even with no row to remove, and the browser tests' clean-up failed
    on it (CI on 2cd814c). A question whose key changed stays, as the ledger that names it does."""
    rng = random.Random(21)
    make = lambda: W.word_1step(rng, RUNG, "Application", 2, structure="PPW_WHOLE")  # noqa: E731
    _, was = _fresh(conn, make)
    keyed_again = _stored(conn, was)
    never, _ = _fresh(conn, make)
    plain = _stored(conn, never)
    story_keys.rekey(conn)
    assert conn.execute("select 1 from item_key_change where item_id = %s", (keyed_again,)).fetchone()
    conn.execute("delete from item where id = %s", (plain,))
    with pytest.raises(psycopg.errors.ForeignKeyViolation), conn.transaction():
        conn.execute("delete from item where id = %s", (keyed_again,))
