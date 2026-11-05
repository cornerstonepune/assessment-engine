"""M0-04c: a sheet code a test makes is unique among every row of the shared test database, so it is made from the
whole random id. Six hex digits of it (24 bits) collided with a row already there and failed a CI shard by chance
(2026-11-03, `test_calibration`, fixed in M0-04); the same line stood in three more test files."""

import re
from pathlib import Path

TESTS = Path(__file__).parent
# "CS" + an id cut short, either as concatenation or inside an f-string
SHORT_CODE = re.compile(r"""("CS"\s*\+\s*[^\n]*hex\[:\d+\])|(f"CS\{[^}\n]*hex\[:\d+\][^}\n]*\})""")


def test_no_test_makes_a_sheet_code_from_a_cut_short_random_id():
    found = [
        f"{p.relative_to(TESTS)}:{n}: {line.strip()}"
        for p in sorted(TESTS.rglob("*.py"))
        if p.name != Path(__file__).name
        for n, line in enumerate(p.read_text().splitlines(), start=1)
        if SHORT_CODE.search(line)
    ]
    assert not found, (
        "a sheet code is unique across the shared test database; use the whole id:\n" + "\n".join(found)
    )
