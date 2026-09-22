"""The server's image holds `engine/` and nothing else (Dockerfile: COPY engine ./engine).

Anything the engine reads while starting from outside that folder stops it on the server: on 2026-09-22
the story templates, read from `supabase/seed/`, kept the engine restarting after step 8 went live.
"""

import os
import pathlib
import shutil
import subprocess
import sys

ENGINE = pathlib.Path(__file__).resolve().parents[1] / "engine"


def test_the_engine_starts_from_its_own_folder_alone(tmp_path):
    shutil.copytree(ENGINE, tmp_path / "engine", ignore=shutil.ignore_patterns("__pycache__"))
    env = {k: v for k, v in os.environ.items() if k not in ("DATABASE_URL", "TEST_DATABASE_URL")}
    r = subprocess.run(
        [sys.executable, "-c", "import engine, engine.api.app; print(engine.__file__)"],
        cwd=tmp_path,
        env={**env, "PYTHONPATH": str(tmp_path)},
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr[-1500:]
    assert r.stdout.strip().startswith(str(tmp_path)), r.stdout  # the copy started, not the repository
