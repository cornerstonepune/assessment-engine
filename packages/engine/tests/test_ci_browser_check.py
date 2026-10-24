"""CI's proof that the browser tests, cut across runners by Playwright's `--shard` (`bin/ci-browser-check`,
goals/ci-browser-shards.yaml), all still ran exactly once: a test missing from every shard, run in two, skipped or
failed twice fails the check; a full, clean split passes it."""

import importlib.machinery
import importlib.util
import pathlib

REPO = pathlib.Path(__file__).resolve().parents[3]
_loader = importlib.machinery.SourceFileLoader("ci_browser_check", str(REPO / "bin" / "ci-browser-check"))
_spec = importlib.util.spec_from_loader("ci_browser_check", _loader)
assert _spec
browser = importlib.util.module_from_spec(_spec)
_loader.exec_module(browser)


def _report(specs, status=None):
    """A Playwright JSON report: one file's specs, each run once with `status`, or listed only when status is None."""
    return {
        "suites": [
            {
                "file": "a.spec.ts",
                "specs": [
                    {
                        "file": "a.spec.ts",
                        "line": line,
                        "title": title,
                        "tests": [
                            {
                                "projectName": project,
                                "status": status or "expected",
                                "results": [{"status": "passed"}] if status else [],
                            }
                        ],
                    }
                    for project, line, title in specs
                ],
            }
        ]
    }


ALL = [("steps", 1, "one"), ("steps", 9, "two"), ("e2e", 1, "one"), ("gate", 4, "three")]
LIST = _report(ALL)


def test_a_full_clean_split_passes():
    assert (
        browser.check(
            LIST, [_report(ALL[:2], "expected"), _report(ALL[2:3], "flaky"), _report(ALL[3:], "expected")]
        )
        == []
    )


def test_the_check_fails_when_a_browser_test_ran_in_no_shard():
    problems = browser.check(LIST, [_report(ALL[:2], "expected"), _report(ALL[2:3], "expected")])
    assert any(p.startswith("ran in no shard") and "three" in p for p in problems)


def test_the_check_fails_when_a_browser_test_ran_in_two_shards():
    problems = browser.check(LIST, [_report(ALL[:3], "expected"), _report(ALL[2:], "expected")])
    assert any(p.startswith("ran in shards [1, 2]") for p in problems)


def test_the_check_fails_when_a_browser_test_was_skipped_or_failed_twice():
    problems = browser.check(LIST, [_report(ALL[:2], "skipped"), _report(ALL[2:], "unexpected")])
    assert sum(p.startswith("skipped") for p in problems) == 2
    assert sum(p.startswith("failed") for p in problems) == 2


def test_the_check_fails_when_the_list_is_empty():
    assert browser.check({"suites": []}, []) == ["the list names no tests"]
