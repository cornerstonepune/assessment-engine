"""CI's cut of the engine's tests across runners (`bin/ci-shard`, goals/ci-engine-shards.yaml): every test lands
in exactly one shard, a file is never split, the runners carry even loads, and the check refuses a suite where a
test dropped out, ran twice, or a shard ran fewer tests than it was given."""

import importlib.machinery
import importlib.util
import json
import pathlib

REPO = pathlib.Path(__file__).resolve().parents[3]
_loader = importlib.machinery.SourceFileLoader("ci_shard", str(REPO / "bin" / "ci-shard"))
_spec = importlib.util.spec_from_loader("ci_shard", _loader)
assert _spec
shard = importlib.util.module_from_spec(_spec)
_loader.exec_module(shard)

IDS = [f"tests/test_{f}.py::test_{i}" for f in "abcdefg" for i in range(3)] + [
    "tests/api/test_h.py::test_x[1-2]"
]
SECONDS = {"tests/test_a.py": 90, "tests/test_b.py": 60, "tests/test_c.py": 50, "tests/test_d.py": 40}


def test_every_test_lands_in_exactly_one_shard_and_no_file_is_cut():
    shards = shard.deal(IDS, SECONDS, 3)
    assert sorted(sum(shards, [])) == sorted(IDS)
    homes = {}
    for k, s in enumerate(shards):
        for i in s:
            homes.setdefault(i.split("::")[0], set()).add(k)
    assert all(len(h) == 1 for h in homes.values())


def test_the_slowest_files_go_to_different_runners_and_the_loads_are_even():
    shards = shard.deal(IDS, SECONDS, 3)
    first = [{i.split("::")[0] for i in s} for s in shards]
    homes = [next(k for k, f in enumerate(first) if f"tests/test_{n}.py" in f) for n in "abc"]
    assert len(set(homes)) == 3
    # the four unknown files count as the average known one (60 s): 420 s in all, so 140 s a runner at best
    usual = sum(SECONDS.values()) / len(SECONDS)
    loads = [sum(SECONDS.get(f, usual) for f in files) for files in first]
    assert max(loads) - min(loads) <= usual


def test_the_cut_is_the_same_on_every_runner():
    assert shard.deal(IDS, SECONDS, 4) == shard.deal(list(IDS), dict(SECONDS), 4)


def test_more_runners_than_files_leaves_some_empty_and_drops_nothing():
    shards = shard.deal(IDS[:3], {}, 4)
    assert sorted(sum(shards, [])) == sorted(IDS[:3]) and sum(1 for s in shards if not s) == 3


def _report(n, skipped=0):
    cases = "".join(
        f'<testcase classname="t" name="t{i}" file="tests/test_a.py" time="1.5"/>' for i in range(n)
    )
    return f'<testsuites><testsuite tests="{n}" skipped="{skipped}">{cases}</testsuite></testsuites>'


def _lay_out(tmp_path, cuts, suite=IDS, ran=None):
    for k, cut in enumerate(cuts, 1):
        d = tmp_path / str(k)
        d.mkdir()
        (d / "collected.txt").write_text("\n".join(suite) + "\n\n22 tests collected in 0.1s\n")
        (d / "assigned.txt").write_text("\n".join(cut) + "\n")
        (d / "report.xml").write_text(_report(len(cut) if ran is None else ran[k - 1]))


def test_the_check_passes_a_suite_run_once(tmp_path, capsys):
    _lay_out(tmp_path, shard.deal(IDS, SECONDS, 3))
    assert shard.main(["check", "3", str(tmp_path)]) == 0
    assert f"every one of the {len(IDS)} tests ran once, across 3 shards" in capsys.readouterr().out


def test_the_check_fails_when_a_test_is_in_no_shard(tmp_path):
    cuts = shard.deal(IDS, SECONDS, 3)
    cuts[0] = cuts[0][1:]
    _lay_out(tmp_path, cuts)
    assert any("is in no shard" in p for p in shard.check(3, tmp_path))


def test_the_check_fails_when_a_test_is_in_two_shards(tmp_path):
    cuts = shard.deal(IDS, SECONDS, 3)
    cuts[1].append(cuts[0][0])
    _lay_out(tmp_path, cuts)
    assert any("ran in shards [1, 2]" in p for p in shard.check(3, tmp_path))


def test_the_check_fails_when_a_shard_ran_fewer_than_it_was_given(tmp_path):
    cuts = shard.deal(IDS, SECONDS, 2)
    _lay_out(tmp_path, cuts, ran=[len(cuts[0]) - 1, len(cuts[1])])
    assert any("ran" in p and "shard 1 was given" in p for p in shard.check(2, tmp_path))


def test_the_check_fails_when_runners_collected_different_suites_or_a_report_is_missing(tmp_path):
    cuts = shard.deal(IDS, SECONDS, 2)
    _lay_out(tmp_path, cuts)
    (tmp_path / "2" / "collected.txt").write_text("\n".join(IDS[:-1]))
    assert "shard 2 collected a different suite" in shard.check(2, tmp_path)
    (tmp_path / "2" / "report.xml").unlink()
    assert shard.main(["check", "2", str(tmp_path)]) == 1


def test_durations_sum_each_file_from_the_reports(tmp_path):
    (tmp_path / "r.xml").write_text(_report(4))
    assert shard.durations([tmp_path / "r.xml"]) == {"tests/test_a.py": 6.0}
    assert json.loads(json.dumps(shard.durations([tmp_path / "r.xml"]))) == {"tests/test_a.py": 6.0}


def test_the_committed_durations_name_real_test_files():
    seconds = json.loads((REPO / ".github" / "ci-durations.json").read_text())
    engine = REPO / "packages" / "engine"
    assert seconds and all((engine / f).is_file() for f in seconds)
