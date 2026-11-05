"""The website's browser tests' K2 timetable (task M1-09): Fortnight 10 as the school wrote it (the frame, the November
planner and the calendar, the fixtures tests/test_k2_timetable_load.py reads), loaded by M1-06's own loader into a
placeholder K2 class of the test's own, built by the loader test's own `loaded()`. Run as a script (`uv run python
tests/k2_timetable_rows.py <section>`). Safe to run twice."""

import sys
import types
from pathlib import Path

# the folder's own name before any `tests.` import, as conftest.py does: an installed package called `tests` (spylls)
# would stand in for it outside pytest
sys.modules["tests"] = types.ModuleType("tests")
sys.modules["tests"].__path__ = [str(Path(__file__).parent)]

from engine.core import db  # noqa: E402
from engine.w2_print import k2_timetable_load as ld  # noqa: E402
from engine.w2_print import k2_timetable_sql as sq  # noqa: E402
from tests.test_k2_timetable_load import loaded  # noqa: E402


def main(section: str, year: str = "2031-32") -> None:
    with db.connect() as conn:
        sq.apply(conn, loaded(), ld.Target("K2", section, year, db.tenant_slug()))
        conn.commit()


if __name__ == "__main__":
    main(*sys.argv[1:])
