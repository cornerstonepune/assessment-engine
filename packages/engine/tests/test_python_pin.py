"""Every `uv` call in CI runs on Python 3.12, the engine image's own (packages/engine/Dockerfile).

On 2026-11-05 GitHub's `ubuntu-latest` image began shipping Python 3.14 at /usr/bin/python3; `uv sync` picked it up and
failed ("paddlepaddle==3.3.1 … only has wheels for cp312, cp313"), first on some jobs and then on main, which stopped
every deploy (run 42060349275). A workflow that does not name the interpreter takes whatever the runner image holds today.
"""

import re
import tomllib

import yaml

from engine.core import db

ENGINE = db.REPO_ROOT / "packages" / "engine"
WORKFLOWS = db.REPO_ROOT / ".github" / "workflows"
USES_UV = re.compile(r"(^|[^\w-])uvx? (sync|run|lock|pip|venv|tool)|astral-sh/setup-uv", re.M)
PINNED = (ENGINE / ".python-version").read_text().strip() if (ENGINE / ".python-version").exists() else None


def test_the_engine_names_its_python_in_a_file_uv_reads():
    assert PINNED == "3.12", "packages/engine/.python-version must name the engine image's Python"
    floor = tomllib.loads((ENGINE / "pyproject.toml").read_text())["project"]["requires-python"]
    assert floor == ">=3.12", f"requires-python {floor} moved: re-check which Python the wheels exist for"
    assert f"FROM python:{PINNED}-slim" in (ENGINE / "Dockerfile").read_text(), (
        "CI and the deployed engine differ"
    )


def test_every_workflow_that_calls_uv_pins_its_python_to_that_file():
    callers = [p for p in sorted(WORKFLOWS.glob("*.yml")) if USES_UV.search(p.read_text())]
    assert {p.name for p in callers} >= {"ci.yml", "rehearse-update-live.yml"}, (
        "the search found too few workflows"
    )
    for path in callers:
        env = yaml.safe_load(path.read_text()).get("env") or {}
        assert str(env.get("UV_PYTHON")) == PINNED, (
            f'{path.name} calls uv without `env: UV_PYTHON: "{PINNED}"` at the top: it takes the runner image\'s Python'
        )
