"""The website reaches the engine only by the routes the engine serves (goals/p1-types-hold.yaml).

`bin/engine contract` writes `apps/web/lib/engine-routes.ts` from the engine's own OpenAPI document; the website's
engine client takes a path and a body only from it, and the website's type check (CI's `tsc`) fails on a route, a
field or a value the engine does not have. Until 2026-10-01 its 36 calls took any string and any body, and four of
them sent a body the engine's route did not declare.
"""

import re

import pytest
import yaml

from engine.api import contract
from engine.core import db

WEB = db.REPO_ROOT / "apps" / "web"


def test_the_websites_list_of_routes_is_what_the_engine_serves():
    """A route added, renamed or given a new field fails here until the list is written again, before the website
    type-checks against a list that is no longer the engine's."""
    assert contract.OUT.read_text() == contract.written(contract.spec()), (
        "the engine changed: run bin/engine contract"
    )


def test_the_list_says_each_body_as_the_engine_checks_it():
    """Required and optional fields, a closed set of values, lists, maps, a model inside a model: each in the
    TypeScript the website is held to. A schema it cannot say stops it rather than becoming `unknown` unseen."""
    defs = {
        "Area": {
            "type": "object",
            "properties": {"skill_set": {"type": "string"}, "n": {"type": "integer"}},
            "required": ["skill_set"],
        }
    }
    body = {
        "type": "object",
        "required": ["verdict", "areas"],
        "properties": {
            "verdict": {"type": "string", "enum": ["keep", "remove"]},
            "areas": {"type": "array", "items": {"$ref": "#/components/schemas/Area"}},
            "note": {"anyOf": [{"type": "string", "maxLength": 300}, {"type": "null"}]},
            "pages": {"type": "array", "items": {"anyOf": [{"type": "integer"}, {"type": "string"}]}},
            "masks": {"type": "object", "additionalProperties": {"type": "number"}},
            "draft": {"type": "object", "additionalProperties": True},
        },
    }
    assert contract.ts(body, defs) == (
        '{ verdict: "keep" | "remove"; areas: { skill_set: string; n?: number }[]; note?: string | null;'
        " pages?: (number | string)[]; masks?: Record<string, number>; draft?: Record<string, unknown> }"
    )
    with pytest.raises(ValueError, match="cannot say"):
        contract.ts({"type": "string", "oneOf": [{"const": "a"}]}, {})


def test_the_website_reaches_the_engine_only_by_its_routes():
    """One client, typed by the list; no other page or action fetches the engine itself; a file of calls that must
    not compile, which `tsc` holds; and CI runs `tsc` on the website."""
    client = (WEB / "lib" / "engine.ts").read_text()
    assert 'import type { EngineRoutes } from "./engine-routes";' in client
    for signature in (
        "engineGet(path: GetPath)",
        "engineImage(path: GetPath)",
        "engineSend<P extends PostPath>(path: P, body: BodyOf<P>)",
        "enginePost<P extends PostPath>(path: P, body: BodyOf<P>)",
    ):
        assert signature in client, signature
    runtime = [p for d in ("app", "lib", "components") for p in (WEB / d).rglob("*.ts*")]
    assert len(runtime) > 50, "found too few of the website's files; the search reads nothing"
    reaching = [p.relative_to(WEB).as_posix() for p in runtime if "ENGINE_URL" in p.read_text()]
    assert reaching == ["lib/engine.ts"]
    refused = re.findall(r"// @ts-expect-error (.+)", (WEB / "tests" / "engine-contract.ts").read_text())
    assert len(refused) >= 6 and any("does not serve" in r for r in refused), refused
    ci = yaml.safe_load((db.REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text())
    assert "npx tsc --noEmit" in [s.get("run") for s in ci["jobs"]["web"]["steps"]]
