"""A child's states and the subject are read from rows, never named in code (goals/b0d-states-and-subject-from-tables.yaml).

Nimish, 2026-10-20: "we need proper tables". B0a made `child_state`; until B0d nothing read it: the states, their
colours, words and order were lists in eleven files of the website and five of the engine, prescriptions were stamped
"NUM", and page headings said "Maths". Each rule a list made is now a column of the row (ADR 0086), and the answers
below are the lists' own, copied from the code they replace on 2026-10-20, so the rows are proved to change nothing.
"""

import ast
import json
import os
import re

import pytest

from engine.core import db, settings, vocabulary
from engine.w2_print import focus_paper, prescribe
from engine.w4_close import card

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")

# The code's answers before B0d (main at e0f7a67), each from the file named.
RAG = {  # apps/web/lib/rag.ts RAG
    "patterned_error": "red",
    "emerging": "red",
    "practising": "amber",
    "secure": "green",
    "stretch_ready": "green",
    "not_enough_yet": "grey",
}
RAG_WORDS = {
    "red": "needs help",
    "amber": "practising",
    "green": "got it",
    "grey": "not enough yet",
}  # rag.ts
COUNT_WORDS = {
    "red": "needs help",
    "amber": "practising",
    "green": "secure",
    "grey": "too few answers",
}  # topics.tsx
STATE_WORDS = {  # apps/web/lib/queries.ts STATE_WORDS
    "not_enough_yet": "not enough yet",
    "patterned_error": "repeating mistake",
    "emerging": "under half right",
    "practising": "practising",
    "secure": "secure",
    "stretch_ready": "ready to move up",
}
LAGGING = ("patterned_error", "emerging", "practising")  # engine/assess/focus.py, weakest first
PROPOSABLE = {"patterned_error", "emerging", "practising", "secure", "stretch_ready"}  # lib/queries-make.ts
STRONG = {"secure", "stretch_ready"}  # engine/w4_close/report.py
WEAKEST_FIRST = (
    "patterned_error",
    "emerging",
    "practising",
    "secure",
    "stretch_ready",
    "not_enough_yet",
)  # card.py
SEVERITY = {  # lib/queries-children.ts, the CASE a skill set takes its worst skill by
    "patterned_error": 1,
    "emerging": 2,
    "practising": 3,
    "not_enough_yet": 4,
    "secure": 5,
    "stretch_ready": 5,
}
GROUPS = {  # engine/w4_close/card.py GROUPS, and patterned_error grouped by its mistake as "reteach"
    "stretch_ready": "move_up",
    "secure": "secure",
    "practising": "practising",
    "emerging": "emerging",
    "not_enough_yet": "not_enough_yet",
    "patterned_error": "reteach",
}
CARD_ORDER = ("move_up", "secure", "practising", "emerging", "reteach", "not_enough_yet")  # card.py ORDER
WHY = {  # engine/w2_print/focus_paper.py WHY, with next_sheet.promote_at 0.8 and demote_below 0.5
    "patterned_error": "the same mistake more than once",
    "emerging": "fewer than half right",
    "practising": "not yet four in five right",
    "secure": "four in five right — a step up",
    "stretch_ready": "ready to move up",
}
MOVE_UP = {"stretch_ready"}  # parent_facts.py: a set ready to move up
NEARLY = {"practising"}  # parent_facts.py and report/parts.tsx: a set that may be nearly secure


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


def test_a_states_rules_are_its_columns_and_give_the_old_answers(conn):
    """Every list the code held is a column of `child_state` or `state_colour`, and gives what the list gave."""
    rows = vocabulary.states(conn)
    by = {s["code"]: s for s in rows}
    assert [s["code"] for s in rows] == list(WEAKEST_FIRST)
    assert {c: s["colour"] for c, s in by.items()} == RAG
    assert {c: s["words"] for c, s in by.items()} == STATE_WORDS
    assert tuple(c for c in WEAKEST_FIRST if by[c]["needs_work"]) == LAGGING
    assert {c for c, s in by.items() if s["enough"]} == PROPOSABLE
    assert {c for c, s in by.items() if s["enough"] and not s["needs_work"]} == STRONG
    assert {c: s["severity"] for c, s in by.items()} == SEVERITY
    assert {c for c, s in by.items() if s["move_up"]} == MOVE_UP
    assert {c for c, s in by.items() if s["nearly"]} == NEARLY
    assert card.groups(rows) == (GROUPS, CARD_ORDER)
    assert focus_paper.reasons(conn) == WHY
    colours = conn.execute("select code, words, count_words from state_colour order by ord").fetchall()
    assert [c["code"] for c in colours] == ["red", "amber", "green", "grey"]
    assert {c["code"]: c["words"] for c in colours} == RAG_WORDS
    assert {c["code"]: c["count_words"] for c in colours} == COUNT_WORDS
    # the seed says the same as the rows, and a school added later has them from the moment it exists
    seeded = settings.seed("vocabulary.json", "child_states")
    assert [s["code"] for s in seeded] == list(WEAKEST_FIRST)
    t = conn.execute("insert into tenant (slug, name) values ('b0d-new', 'B0d') returning id").fetchone()[
        "id"
    ]
    got = conn.execute(
        "select code, enough, severity, move_up, nearly, card_group, why from child_state where tenant_id = %s order by ord",
        (t,),
    ).fetchall()
    assert [tuple(r.values()) for r in got] == [
        (s["code"], s["enough"], s["severity"], s["move_up"], s["nearly"], s["card_group"], s.get("why"))
        for s in seeded
    ]
    assert (
        conn.execute("select count(*) as n from state_colour where tenant_id = %s", (t,)).fetchone()["n"] == 4
    )


def test_one_state_says_too_few_answers_and_a_colour_is_a_key(conn):
    """A skill with no state yet reads as the one state with too few answers; a state's colour must be a colour row."""
    t = conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]
    with pytest.raises(Exception, match="child_state_one_too_few"):
        with conn.transaction():
            conn.execute(
                "insert into child_state (tenant_id, code, ord, words, colour, needs_work, enough, severity,"
                " move_up, nearly, card_group) values (%s, 'b0d_x', 9, 'x', 'grey', false, false, 4, false, false, 'x')",
                (t,),
            )
    with pytest.raises(Exception, match="child_state_tenant_id_colour_fkey"):
        with conn.transaction():
            conn.execute("update child_state set colour = 'violet' where tenant_id = %s and ord = 0", (t,))


def test_a_state_reworded_in_its_row_is_reworded_on_the_paper(conn):
    """The reason a paper prints is the row's, its share in words from the threshold row: a new wording or a new
    threshold is an update, and no code changes."""
    code = vocabulary.states(conn)[2]["code"]
    conn.execute(
        "update child_state set why = 'still short of {next_sheet.promote_at}' where code = %s", (code,)
    )
    conn.execute("update threshold set value = 0.75 where key = 'next_sheet.promote_at'")
    assert focus_paper.reasons(conn)[code] == "still short of three in four"


@pytest.fixture
def child(conn):
    t = conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]
    return conn.execute(
        "insert into child (tenant_id, roll_no, section, band) values (%s, '1', 'B0DSEC', 'G2') returning id",
        (t,),
    ).fetchone()["id"]


def test_a_prescription_takes_its_subject_from_the_skills_topic(conn, child):
    """skill_set → topic → subject: a skill set moved to a topic of another subject is prescribed as that subject."""
    s = conn.execute(
        "select code, topic_code, tenant_id from skill_set where topic_code is not null limit 1"
    ).fetchone()
    want = conn.execute("select subject_code from topic where code = %s", (s["topic_code"],)).fetchone()[
        "subject_code"
    ]
    prescribe.for_class(conn, "B0DSEC", "B0D-W1", s["code"])
    got = conn.execute("select strand from prescription where child_id = %s", (child,)).fetchone()["strand"]
    assert got == want
    conn.execute(
        "insert into subject (tenant_id, code, name, label) values (%s, 'B0DSUBJ', 'Another subject', 'Another')",
        (s["tenant_id"],),
    )
    conn.execute(
        "insert into topic (tenant_id, code, name, subject_code, ord) values (%s, 'B0D.T', 'B0d topic', 'B0DSUBJ', 99)",
        (s["tenant_id"],),
    )
    conn.execute("update skill_set set topic_code = 'B0D.T' where code = %s", (s["code"],))
    prescribe.for_class(conn, "B0DSEC", "B0D-W2", s["code"])
    got = conn.execute(
        "select strand from prescription where child_id = %s and week = 'B0D-W2'", (child,)
    ).fetchone()
    assert got["strand"] == "B0DSUBJ"


# ---- the scan: no file outside the tests, the migrations and the seed names a state or a subject

ENGINE = db.REPO_ROOT / "packages" / "engine" / "engine"
WEB = db.REPO_ROOT / "apps" / "web"
WEB_DIRS = ("app", "lib", "components")
# The engineering map (workflows.json, drawn at /workflows) says which steps of the engine work for one subject only:
# a fact about the engine's code, not a word the school's pages take from a subject.
EXEMPT = {WEB / "app" / "(app)" / "workflows" / "page.tsx"}


def _vocabulary():
    states = [s["code"] for s in settings.seed("vocabulary.json", "child_states")]
    subjects = settings.seed("subjects.json", "subjects")
    codes = [s["code"] for s in subjects]
    # a subject's label, as its pages say it, and the words a page has used for it ("Mathematics — Number" is a name
    # of many words, "Number" among them, which a page uses for numbers)
    names = sorted({s["label"] for s in subjects} | {"Maths", "Mathematics"})
    return states, codes, names


def _python_strings(path):
    """Every string constant in a module that is not a docstring."""
    tree = ast.parse(path.read_text())
    docs = {
        id(n.body[0].value)
        for n in ast.walk(tree)
        if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        and n.body
        and isinstance(n.body[0], ast.Expr)
        and isinstance(n.body[0].value, ast.Constant)
    }
    return [
        (n.lineno, n.value)
        for n in ast.walk(tree)
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docs
    ]


COMMENT = re.compile(r"/\*.*?\*/|(?<![:\"'`\\])//[^\n]*|\{/\*.*?\*/\}", re.S)


def _hits_in(text, states, codes, names):
    """What in a piece of code names a state or a subject: a state's code as a quoted word, or as a key or a name
    where it has an underscore (no English word has); a subject's code quoted; a subject's name anywhere."""
    out = []
    for s in states:
        quoted = rf"(['\"`]){re.escape(s)}\1"
        if re.search(quoted, text) or ("_" in s and re.search(rf"\b{re.escape(s)}\b", text)):
            out.append(s)
    out += [c for c in codes if re.search(rf"(['\"`]){re.escape(c)}\1", text)]
    out += [n for n in names if re.search(rf"\b{n}\b", text)]
    return out


def _engine_hits(states, codes, names):
    """Where the engine's code names a state or a subject: a string that is one, or holds one, and a variable named
    after a state."""
    found = []
    for path in sorted(ENGINE.rglob("*.py")):
        where = path.relative_to(db.REPO_ROOT)
        for line, value in _python_strings(path):
            exact = [value] if value in states or value in codes else []
            found += [
                f"{where}:{line} names {hit!r}" for hit in exact + _hits_in(value, states, codes, names)
            ]
        found += [
            f"{where}:{n.lineno} names {n.id!r}"
            for n in ast.walk(ast.parse(path.read_text()))
            if isinstance(n, ast.Name) and "_" in n.id and n.id in states
        ]
    return found


def _web_hits(states, codes, names):
    """Where the website's code names a state or a subject, its comments aside."""
    found = []
    for d in WEB_DIRS:
        for path in sorted([*(WEB / d).rglob("*.ts"), *(WEB / d).rglob("*.tsx")]):
            if path in EXEMPT:
                continue
            code = COMMENT.sub(lambda m: "\n" * m.group().count("\n"), path.read_text())
            for i, text in enumerate(code.splitlines(), 1):
                found += [
                    f"{path.relative_to(db.REPO_ROOT)}:{i} names {hit!r}"
                    for hit in _hits_in(text, states, codes, names)
                ]
    return found


def test_no_file_names_a_state_or_a_subject():
    """A state is named by its row, a subject by the skill's topic: no code says "practising", "NUM" or "Maths"."""
    vocab = _vocabulary()
    found = _engine_hits(*vocab) + _web_hits(*vocab)
    assert not found, "\n".join(dict.fromkeys(found))


def test_the_scan_sees_what_it_should():
    """The scan is not blind: it finds each way a file used to name a state or a subject, and passes prose."""
    states, codes, names = _vocabulary()
    for named in [
        "if s['state'] == 'secure':",
        'const RAG = { patterned_error: "red" }',
        "where k.domain = 'NUM'",
        "<div>Grade 1–4 · Maths</div>",
        'state = any(${["practising"]})',
        json.dumps({"emerging": 1}),
    ]:
        assert _hits_in(named, states, codes, names), named
    for prose in ["a skill still practising it", "secure once it holds on another", "MISSING.NUM"]:
        assert not _hits_in(prose, states, codes, names), prose
