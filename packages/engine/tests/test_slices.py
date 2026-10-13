"""M5e: the files each × ÷ slice changed, per part of the map (BUILD-ORDER: "The score is the files each slice changed,
per workflow, recorded in STATE.md at M5"). The parts are `workflows.json`'s: a workflow by its folder, a shared part by
its folder or its files; beside them the website, the rows the loader reads, the schema, the tests and the docs."""

from engine.checks import slices

LOG = (
    "\x1eM4c: multiples and factors\n\n"
    "packages/engine/engine/assess/multiples.py\n"
    "packages/engine/engine/w2_print/library.py\n"
    "packages/engine/tests/test_multiples.py\n"
    "supabase/seed/skill_sets.json\n"
    "\x1eM4c's record: built and proved on copies\n\n"
    "STATE.md\n"
    "packages/engine/engine/assess/multiples.py\n"
    "\x1eM&D: the taxonomy drafted\n\n"
    "docs/md-taxonomy.md\n"
    "\x1eUI6b: no long lists\n\n"
    "apps/web/app/(app)/page.tsx\n"
    "\x1eM5b: a paper printed for a child comes back\n\n"
    "packages/engine/engine/w3_read/copies.py\n"
    "packages/engine/engine/cli.py\n"
    "apps/web/components/question.tsx\n"
    "apps/web/tests/m5-every-kind-draws.spec.ts\n"
    "supabase/migrations/20261012_x.sql\n"
    "goals/md5b-read-back.yaml\n"
)


def test_a_file_is_placed_in_its_part_of_the_map():
    place = slices.placer()
    assert place("packages/engine/engine/w3_read/copies.py") == "W3"
    assert place("packages/engine/engine/w4_close/card.py") == "W4"
    assert place("packages/engine/engine/assess/multiples.py") == "assess"
    assert place("packages/engine/engine/cli.py") == "doors", "a shared part's own files, beside its folder"
    assert place("packages/engine/engine/api/routes/capture.py") == "doors"
    assert place("packages/engine/tests/test_slices.py") == "tests"
    assert place("apps/web/tests/m5-every-kind-draws.spec.ts") == "tests"
    assert place("apps/web/components/question.tsx") == "website"
    assert place("supabase/seed/skill_sets.json") == "rows"
    assert place("supabase/migrations/20261012_x.sql") == "schema"
    assert place("goals/md5b-read-back.yaml") == "docs" and place("STATE.md") == "docs"
    assert place("workflows.json") == "map" and place("research/md_rows.py") == "research"
    assert place(".github/workflows/ci.yml") == "ci" and place("README") == "other"


def test_each_slice_counts_each_file_it_changed_once_and_only_the_slices_of_multiplication_and_division():
    got = slices.changed(LOG)
    assert set(got) == {"M4c", "M5b"}, "M&D's taxonomy and the website's UI slices are not × ÷ build slices"
    assert got["M4c"] == {
        "packages/engine/engine/assess/multiples.py",
        "packages/engine/engine/w2_print/library.py",
        "packages/engine/tests/test_multiples.py",
        "supabase/seed/skill_sets.json",
        "STATE.md",
    }, "its record's commit counts as the slice's, and a file twice counts once"


def test_the_score_is_a_count_per_part_for_each_slice_in_the_order_built():
    rows = slices.score(slices.changed(LOG), slices.placer())
    assert [r["slice"] for r in rows] == ["M4c", "M5b"]
    assert rows[0]["parts"] == {"assess": 1, "W2": 1, "tests": 1, "rows": 1, "docs": 1}
    assert rows[1]["parts"] == {"W3": 1, "doors": 1, "website": 1, "tests": 1, "schema": 1, "docs": 1}
    assert rows[1]["files"] == 6
