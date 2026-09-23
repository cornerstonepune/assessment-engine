"""The areas a child's next paper works on, read from the child's own graph (goal s11-focus-paper).

Pure: graph rows in, areas out. The catalog is the bank's skill sets as the database describes them — the
rung each sits on, its place on the ladder, the skill it is for, and every skill its questions use.
"""

from engine.assess.focus import Area, areas, home, skill_set_for

CATALOG = [
    {
        "code": "ADD.2D2D",
        "rung": "R5",
        "order": 5,
        "own": "NUM.OPS.01",
        "skills": {"NUM.OPS.01", "NUM.OPS.05"},
    },
    {
        "code": "SUB.2D2D",
        "rung": "R6",
        "order": 6,
        "own": "NUM.OPS.02",
        "skills": {"NUM.OPS.02", "NUM.MEAS.04"},
    },
    {
        "code": "WORD.1_2STEP",
        "rung": "R8",
        "order": 8,
        "own": "NUM.PRB.02",
        "skills": {"NUM.PRB.02", "NUM.MEAS.04"},
    },
    {
        "code": "ADD.3D3D",
        "rung": "R9",
        "order": 9,
        "own": "NUM.OPS.01",
        "skills": {"NUM.OPS.01", "NUM.OPS.05"},
    },
    {"code": "SUB.3D3D", "rung": "R10", "order": 10, "own": "NUM.OPS.02", "skills": {"NUM.OPS.02"}},
    {"code": "WORD.BUDGET", "rung": "R14", "order": 14, "own": "NUM.MEAS.04", "skills": {"NUM.MEAS.04"}},
    {"code": "REASON.EXPLAIN", "rung": "X1", "order": None, "own": "NUM.PRB.03", "skills": {"NUM.PRB.03"}},
]
RULE = {"most": 3, "reach": 2, "easy_below": 0.5}


def row(skill, rung, state, right, answered, mistake=None):
    return {
        "skill_code": skill,
        "rung_code": rung,
        "state": state,
        "n_correct": right,
        "n_events": answered,
        "repeating_misconception": mistake,
    }


def test_a_skill_the_child_lags_in_becomes_an_area_to_work_on():
    graph = [
        row("NUM.OPS.01", "R5", "emerging", 3, 9),
        row("NUM.OPS.02", "R6", "secure", 9, 10),
        row("NUM.OPS.01", "R9", "not_enough_yet", 1, 2),
        row("NUM.OPS.02", "R10", "stretch_ready", 12, 12),
    ]
    assert [a.skill_set for a in areas(graph, CATALOG, RULE)] == ["ADD.2D2D"]


def test_the_weakest_areas_come_first_at_a_level_set_by_how_often_the_child_was_right():
    graph = [
        row("NUM.OPS.01", "R5", "practising", 7, 10),
        row("NUM.OPS.02", "R6", "emerging", 2, 8),
        row("NUM.OPS.01", "R9", "patterned_error", 6, 10, "M_NOCARRY"),
        row("NUM.PRB.02", "R8", "practising", 6, 10),
    ]
    got = areas(graph, CATALOG, RULE)
    # a repeated mistake first, then fewer than half right, then not yet four in five — and no more than three
    assert [(a.skill_set, a.level) for a in got] == [
        ("ADD.3D3D", "Medium"),
        ("SUB.2D2D", "Easy"),
        ("WORD.1_2STEP", "Medium"),
    ]
    assert got[0] == Area("ADD.3D3D", "NUM.OPS.01", "Medium", 6, 10, "M_NOCARRY", "patterned_error")


def test_a_weak_subtraction_on_an_addition_rung_is_worked_on_as_subtraction():
    # Old papers put 3-digit subtraction on R9, the rung of 3-digit addition. Read by rung alone, a child's
    # subtraction mistakes were charged to addition; read by skill, they go to subtraction's own set.
    assert skill_set_for("NUM.OPS.02", "R9", CATALOG, RULE["reach"]) == "SUB.3D3D"
    assert skill_set_for("NUM.OPS.01", "R9", CATALOG, RULE["reach"]) == "ADD.3D3D"
    # money on a Grade 2 story stays with stories on that rung, not a 4-digit budget six rungs up
    assert skill_set_for("NUM.MEAS.04", "R8", CATALOG, RULE["reach"]) == "WORD.1_2STEP"
    # a rung off the ladder is matched on the rung itself
    assert skill_set_for("NUM.PRB.03", "X1", CATALOG, RULE["reach"]) == "REASON.EXPLAIN"
    assert skill_set_for("NUM.OPS.03", "R9", CATALOG, RULE["reach"]) is None


def test_the_same_area_read_twice_is_worked_on_once_at_its_weakest():
    graph = [row("NUM.OPS.02", "R9", "practising", 7, 10), row("NUM.OPS.02", "R10", "emerging", 1, 6)]
    got = areas(graph, CATALOG, RULE)
    assert [(a.skill_set, a.state, a.level) for a in got] == [("SUB.3D3D", "emerging", "Easy")]


def test_a_child_who_lags_nowhere_is_given_no_areas():
    assert areas([row("NUM.OPS.01", "R5", "secure", 9, 10)], CATALOG, RULE) == []


HOME = {**RULE, "stretch": {"secure": "Hard", "stretch_ready": "Advance"}}
LEVELS = {c["code"]: ("Easy", "Medium", "Hard", "Advance") for c in CATALOG}


def test_a_home_paper_is_one_skill_never_a_mix_the_weakest():
    graph = [
        row("NUM.OPS.01", "R5", "practising", 6, 10),
        row("NUM.OPS.02", "R6", "patterned_error", 3, 10, "M_SMALL_FROM_LARGE"),
        row("NUM.OPS.02", "R10", "emerging", 2, 6),
    ]
    got = home(graph, CATALOG, HOME, LEVELS)
    assert [(a.skill_set, a.level, a.mistake) for a in got] == [("SUB.2D2D", "Easy", "M_SMALL_FROM_LARGE")]


def test_a_child_who_lags_nowhere_is_stretched_on_their_strongest_skill_one_level_up():
    graph = [row("NUM.OPS.01", "R5", "secure", 9, 10), row("NUM.OPS.02", "R6", "stretch_ready", 10, 10)]
    assert [(a.skill_set, a.level) for a in home(graph, CATALOG, HOME, LEVELS)] == [("SUB.2D2D", "Advance")]
    only_secure = [row("NUM.OPS.01", "R5", "secure", 9, 10)]
    assert [(a.skill_set, a.level) for a in home(only_secure, CATALOG, HOME, LEVELS)] == [
        ("ADD.2D2D", "Hard")
    ]


def test_a_stretch_takes_the_hardest_level_the_skill_defines_up_to_its_target():
    """1-digit + 1-digit has no Hard: a secure child is stretched at Medium, not handed a level that is not there."""
    levels = {**LEVELS, "ADD.2D2D": ("Easy", "Medium", "Advance")}
    got = home([row("NUM.OPS.01", "R5", "secure", 9, 10)], CATALOG, HOME, levels)
    assert [(a.skill_set, a.level) for a in got] == [("ADD.2D2D", "Medium")]


def test_a_child_with_too_little_work_gets_no_home_paper():
    assert home([row("NUM.OPS.01", "R5", "not_enough_yet", 1, 2)], CATALOG, HOME, LEVELS) == []
