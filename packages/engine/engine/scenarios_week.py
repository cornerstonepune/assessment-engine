"""W2's scenarios: does a week's worth of paper hold up? `engine goal w2-assemble-and-print`.

Every check builds a real week for a throwaway section — prescribe, assemble, store — inside the
caller's transaction, and rolls it back. Nothing here mocks the engine: the properties are read off
the rows the real path writes, which is the only way to catch what the parts' own tests cannot.
"""

from engine import assemble, db, prescribe

SECTION = "GOALSEC"
WEEK = "goal-week"
SET = "SUB.2D.EXCH"


def _config(conn, key, default):
    row = conn.execute("select value from config where key = %s", (key,)).fetchone()
    return default if row is None else row["value"]


def _children(conn, n, band="G2"):
    """A section of its own, so no scenario can touch the school's real roster."""
    tenant = conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]
    conn.execute("delete from child where section = %s", (SECTION,))
    ids = []
    for i in range(1, n + 1):
        row = conn.execute(
            "insert into child (tenant_id, roll_no, section, band) values (%s,%s,%s,%s) returning id",
            (tenant, str(i), SECTION, band),
        ).fetchone()
        conn.execute(
            "insert into pii.child (tenant_id, child_id, first_name) values (%s,%s,%s)",
            (tenant, row["id"], f"Child {i}"),
        )
        ids.append(row["id"])
    return ids


def _week(conn, sc, band=None):
    """One real week: children, prescriptions, assembled sheets. Returns (prescriptions, built)."""
    n = int(sc.get("children", 10))
    _children(conn, n, band or sc.get("band", "G2"))
    rx = prescribe.for_class(conn, SECTION, WEEK, sc.get("skill_set", SET))
    built = assemble.for_week(conn, SECTION, WEEK)
    return rx, built


def _sheet_items(sheet):
    return [str(r["id"]) for r in sheet["item_rows"]]


def _headroom(conn, rx):
    """How many questions the class needs against how many the unit holds — the number that decides
    whether ten children can have ten different papers at all."""
    per_sheet = int(_config(conn, "assemble.items_per_sheet", 12))
    spares = int(_config(conn, "assemble.spares_per_difficulty", 2))
    needed, held = 0, 0
    for difficulty in {p["difficulty"] for p in rx}:
        kids = sum(1 for p in rx if p["difficulty"] == difficulty)
        needed += (kids + spares) * per_sheet
        held += conn.execute(
            "select count(*) as n from item where status = 'active' and skill_set_code = %s"
            " and difficulty = %s",
            (rx[0]["skill_set"] if "skill_set" in rx[0] else SET, difficulty),
        ).fetchone()["n"]
    return needed, held


def no_two_children_share_a_question(conn, sc):
    rx, built = _week(conn, sc)
    needed, held = _headroom(conn, rx)
    seen, clashes = {}, []
    for sheet in built["sheets"]:
        for item in _sheet_items(sheet):
            if item in seen:
                clashes.append(f"{sheet['roll_no']} and {seen[item]} both have {item[:8]}")
            seen[item] = sheet["roll_no"]
    m = {
        "children": len(rx),
        "papers": len(built["sheets"]),
        "questions_needed": needed,
        "questions_held": held,
        "short": len(built["short"]),
    }
    fails = []
    if clashes:
        fails.append(f"{len(clashes)} shared questions: {clashes[:3]}")
    if len(built["sheets"]) != len(rx):
        fails.append(f"{len(rx) - len(built['sheets'])} children got no paper: {built['short'][:3]}")
    return m, fails


def qr_is_unique_and_resolves(conn, sc):
    _, built = _week(conn, sc)
    sheets = built["sheets"] + built["spares"]
    qrs = [s["qr"] for s in sheets]
    fails = []
    if len(set(qrs)) != len(qrs):
        fails.append(f"{len(qrs) - len(set(qrs))} sheets share a QR code")
    for s in sheets:
        row = conn.execute(
            "select child_id, sheet_template_id from sheet_instance where qr_code = %s", (s["qr"],)
        ).fetchall()
        if len(row) != 1:
            fails.append(f"{s['qr']} resolves to {len(row)} sheets")
        elif str(row[0]["child_id"]) != str(s["child_id"]) and (row[0]["child_id"] or s["child_id"]):
            fails.append(f"{s['qr']} points at the wrong child")
    return {"sheets": len(sheets), "distinct_qr": len(set(qrs))}, fails


def key_matches_every_sheet(conn, sc):
    """The key a teacher marks from is the answers of the questions on the page, in that order. Here
    that reduces to: the stored template holds exactly the questions the child was given, and every
    one of them has exactly one answer to mark against. The rendering itself is `test_render_pdf`."""
    _, built = _week(conn, sc)
    fails, answers = [], 0
    for s in built["sheets"] + built["spares"]:
        stored = conn.execute(
            "select item_ids from sheet_template where id = %s", (s["template_id"],)
        ).fetchone()["item_ids"]
        if [str(x) for x in stored] != _sheet_items(s):
            fails.append(f"{s['qr']}: the stored sheet is not the questions the child was given")
        for r in s["item_rows"]:
            marks = [x for x in r["responses"] if x.get("answer") not in (None, "")]
            answers += len(marks)
            if len(marks) != 1:
                fails.append(f"{s['qr']}: {r['item_key']} has {len(marks)} answers to mark")
    return {"sheets": len(built["sheets"]) + len(built["spares"]), "answers_on_the_key": answers}, fails


def respects_exposure_window(conn, sc):
    """Two weeks in a row for the same children: nothing a child saw in week one may come back in
    week two. Built as two real weeks rather than by clearing the first — a prescription points at
    the sheet it produced, so deleting one is neither possible nor what a school ever does.
    """
    rx, built = _week(conn, sc)
    if not built["sheets"]:
        return {"children": len(rx)}, ["no sheets were built, so nothing could be checked"]
    seen = {s["roll_no"]: set(_sheet_items(s)) for s in built["sheets"]}
    prescribe.for_class(conn, SECTION, WEEK + "-2", sc.get("skill_set", SET))
    again = assemble.for_week(conn, SECTION, WEEK + "-2")
    fails, checked = [], 0
    for sheet in again["sheets"]:
        before = seen.get(sheet["roll_no"])
        if before is None:
            continue
        checked += 1
        repeats = before & set(_sheet_items(sheet))
        if repeats:
            fails.append(f"{sheet['roll_no']} saw {len(repeats)} question(s) again in the second week")
    if not checked:
        fails.append(
            f"no child got a paper in both weeks ({len(again['short'])} short), so the window"
            " was never exercised — the unit does not hold two weeks for this class"
        )
    return {
        "children": len(rx),
        "children_checked_across_two_weeks": checked,
        "window_days": _config(conn, "exposure.days", 21),
    }, fails


def sheet_length_matches_config(conn, sc):
    _, built = _week(conn, sc)
    want = int(_config(conn, "assemble.items_per_sheet", 12))
    wrong = [
        f"{s['qr']}: {len(s['item_rows'])}"
        for s in built["sheets"] + built["spares"]
        if len(s["item_rows"]) != want
    ]
    return {"questions_per_sheet": want, "sheets": len(built["sheets"]) + len(built["spares"])}, (
        [f"{len(wrong)} sheets are not {want} questions long: {wrong[:3]}"] if wrong else []
    )


def spares_are_anonymous(conn, sc):
    rx, built = _week(conn, sc)
    want_each = int(_config(conn, "assemble.spares_per_difficulty", 2))
    difficulties = {p["difficulty"] for p in rx}
    named = [s["qr"] for s in built["spares"] if s["child_id"]]
    fails = []
    if named:
        fails.append(f"{len(named)} spare sheets carry a child: {named[:3]}")
    if len(built["spares"]) != want_each * len(difficulties):
        fails.append(
            f"{len(built['spares'])} spares for {len(difficulties)} difficulties,"
            f" expected {want_each * len(difficulties)}"
        )
    return {"spares": len(built["spares"]), "difficulties": len(difficulties)}, fails


def names_the_child_it_could_not_fill(conn, sc):
    """A short pool must produce a named child, never a short paper.

    Two ways in: a rung whose whole number range is smaller than a class needs (`skill_set` in the
    scenario — a G1 rung really is that small, ADR 0016), or an artificially emptied pool when the
    scenario names none.
    """
    if sc.get("skill_set"):
        rx, built = _week(conn, sc)
        fails = []
        if not built["short"]:
            fails.append(f"nothing was reported short, so this unit does hold {len(rx)} papers")
        if len(built["sheets"]) + len(built["short"]) != len(rx):
            fails.append(
                f"{len(rx)} children, {len(built['sheets'])} papers, {len(built['short'])} named"
                " — someone is unaccounted for"
            )
        for s in built["short"]:
            if "had" not in s or "needed" not in s:
                fails.append(f"roll {s.get('roll_no')} is named short without saying how many were missing")
        return {
            "children": len(rx),
            "papers": len(built["sheets"]),
            "named_short": len(built["short"]),
            "skill_set": sc["skill_set"],
        }, fails
    sc = {**sc, "children": 2}
    _children(conn, 2)
    rx = prescribe.for_class(conn, SECTION, WEEK, SET)
    difficulty = rx[0]["difficulty"]
    keep = conn.execute(
        "select id from item where status = 'active' and skill_set_code = %s and difficulty = %s"
        " order by item_key limit 5",
        (SET, difficulty),
    ).fetchall()
    conn.execute(
        "update item set status = 'retired' where status = 'active' and skill_set_code = %s"
        " and difficulty = %s and id <> all(%s)",
        (SET, difficulty, [r["id"] for r in keep]),
    )
    built = assemble.for_week(conn, SECTION, WEEK)
    fails = []
    if built["sheets"]:
        fails.append(f"{len(built['sheets'])} papers were printed from a pool of 5 questions")
    if len(built["short"]) != len(rx):
        fails.append(f"{len(built['short'])} children named short, expected {len(rx)}")
    elif any("had" not in s or "needed" not in s for s in built["short"]):
        fails.append("a short child is named without saying how many questions were missing")
    return {"pool_left": len(keep), "named_short": len(built["short"])}, fails


def falls_back_to_the_band_default(conn, sc):
    rx, _ = _week(conn, sc)
    wrong = [f"{p['roll_no']}: {p['rule']}" for p in rx if p["rule"] != "band_default"]
    return {"children": len(rx), "on_the_band_default": len(rx) - len(wrong)}, (
        [f"{len(wrong)} children with no evidence were not given the band default: {wrong[:3]}"]
        if wrong
        else []
    )


def nothing_prints_until_a_person_approves(conn, sc):
    """N7's gate, checked from both sides: a sheet cannot be marked printed with no approver, and one
    approval covers the week and names the person on every sheet in it."""
    import psycopg

    _, built = _week(conn, sc)
    qrs = [s["qr"] for s in built["sheets"] + built["spares"]]
    fails = []
    before = conn.execute(
        "select count(*) as n from sheet_instance where qr_code = any(%s) and print_status <> 'new'",
        (qrs,),
    ).fetchone()["n"]
    if before:
        fails.append(f"{before} sheets were already printable before anyone approved them")
    conn.execute("savepoint no_approver")  # its own statement: psycopg prepares one command at a time
    try:
        conn.execute("update sheet_instance set print_status = 'printed' where qr_code = %s", (qrs[0],))
        fails.append("a sheet was printed with nobody's name on it")
    except psycopg.errors.CheckViolation:
        pass
    conn.execute("rollback to savepoint no_approver")

    out = assemble.approve(conn, SECTION, WEEK, "practice", "a test")
    rows = conn.execute(
        "select print_status, approved_by from sheet_instance where qr_code = any(%s)", (qrs,)
    ).fetchall()
    unsigned = [r for r in rows if r["print_status"] == "printed" and not r["approved_by"]]
    if unsigned:
        fails.append(f"{len(unsigned)} approved sheets do not say who approved them")
    if out["sheets"] != len(qrs):
        fails.append(f"one approval covered {out['sheets']} of {len(qrs)} sheets")
    return {"sheets": len(qrs), "approved": out["sheets"], "by": out["approved_by"]}, fails


def prints_in_roll_order(conn, sc):
    _, built = _week(conn, sc)
    order = [int(s["roll_no"]) for s in built["sheets"] if str(s["roll_no"]).isdigit()]
    return {"papers": len(order)}, (
        [f"the pack is out of roll order: {order}"] if order != sorted(order) else []
    )


CHECKS = {
    fn.__name__: fn
    for fn in (
        no_two_children_share_a_question,
        qr_is_unique_and_resolves,
        key_matches_every_sheet,
        respects_exposure_window,
        sheet_length_matches_config,
        spares_are_anonymous,
        names_the_child_it_could_not_fill,
        falls_back_to_the_band_default,
        nothing_prints_until_a_person_approves,
        prints_in_roll_order,
    )
}


def run(conn, sc):
    must = sc.get("must")
    if must not in CHECKS:
        return {"must": must}, [f"no check named {must!r} — the goal asks for something nothing proves"]
    try:
        m, fails = CHECKS[must](conn, sc)
    finally:
        conn.rollback()  # a scenario proves the week, it never leaves one behind
    return m, fails
