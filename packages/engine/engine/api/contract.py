"""The website's list of the engine's routes, written from the engine itself (goals/p1-types-hold.yaml).

`bin/engine contract` writes `apps/web/lib/engine-routes.ts`: every route's method and path, and the body a POST
takes, as TypeScript. The website's engine client (`apps/web/lib/engine.ts`) accepts only these, so the website's
type check fails on a route the engine does not serve or a field a body does not have, and
`tests/test_contract.py` fails the day the file is not what the engine says. A schema this cannot say in
TypeScript stops it, never becomes `unknown` unseen.
"""

import json
from typing import Any

from engine.core import db

OUT = db.REPO_ROOT / "apps" / "web" / "lib" / "engine-routes.ts"
HEAD = (
    "// The engine's routes, written by `bin/engine contract` from the engine itself (packages/engine/engine/api)\n"
    "// and never by hand: packages/engine/tests/test_contract.py fails the day this is not what the engine serves.\n"
    "// lib/engine.ts takes a path and a body only from here.\n"
)
# Constraints TypeScript cannot hold; the engine still checks each of them on every request.
_UNSAID = {"title", "description", "default", "examples", "format", "minLength", "maxLength", "minItems"}
_UNSAID |= {
    "maxItems",
    "minimum",
    "maximum",
    "exclusiveMinimum",
    "exclusiveMaximum",
    "propertyNames",
    "pattern",
}
_SCALARS = {"string": "string", "integer": "number", "number": "number", "boolean": "boolean", "null": "null"}


def ts(schema: dict[str, Any], defs: dict[str, Any]) -> str:
    """One JSON schema, as FastAPI writes a request body's, → its TypeScript type."""
    said = {k: v for k, v in schema.items() if k not in _UNSAID}
    if "$ref" in said:
        return ts(defs[said["$ref"].rsplit("/", 1)[1]], defs)
    if "anyOf" in said:
        return " | ".join(ts(s, defs) for s in said["anyOf"])
    if "enum" in said:
        return " | ".join(json.dumps(v) for v in said["enum"])
    if "const" in said:
        return json.dumps(said["const"])
    return _one_kind(said, defs) if said else "unknown"


def _one_kind(said: dict[str, Any], defs: dict[str, Any]) -> str:
    """A schema naming one kind of value — a scalar, a list, a tuple or an object — with what TypeScript cannot hold
    already set aside."""
    kind, keys = said.get("type"), set(said)
    if kind in _SCALARS and keys == {"type"}:
        return _SCALARS[kind]
    if kind == "array" and "prefixItems" in said:
        return "[" + ", ".join(ts(s, defs) for s in said["prefixItems"]) + "]"
    if kind == "array" and keys == {"type", "items"}:
        inner = ts(said["items"], defs)
        return f"({inner})[]" if _union(said["items"], defs) else f"{inner}[]"
    if kind == "object" and keys <= {"type", "properties", "required"}:
        need = set(said.get("required", []))
        fields = [
            f"{k}{'' if k in need else '?'}: {ts(v, defs)}" for k, v in said.get("properties", {}).items()
        ]
        return "{ " + "; ".join(fields) + " }" if fields else "Record<string, never>"
    if kind == "object" and keys == {"type", "additionalProperties"}:
        values = said["additionalProperties"]
        return f"Record<string, {'unknown' if values is True else ts(values, defs)}>"
    raise ValueError(f"the contract cannot say this schema in TypeScript: {said}")


def _union(schema: dict[str, Any], defs: dict[str, Any]) -> bool:
    """Whether `ts` says this as `A | B`, which an array of it must bracket."""
    if "$ref" in schema:
        return _union(defs[schema["$ref"].rsplit("/", 1)[1]], defs)
    return len(schema.get("anyOf", schema.get("enum", []))) > 1


def routes(spec: dict[str, Any]) -> dict[str, str]:
    """`"POST /papers/plan"` → the body it takes, as TypeScript (`null` for none), for every route the engine serves."""
    defs = spec.get("components", {}).get("schemas", {})
    out: dict[str, str] = {}
    for path, ops in spec["paths"].items():
        for method, op in ops.items():
            body = op.get("requestBody", {}).get("content", {}).get("application/json", {}).get("schema")
            out[f"{method.upper()} {path}"] = "null" if body is None else ts(body, defs)
    return dict(sorted(out.items()))


def written(spec: dict[str, Any]) -> str:
    """The whole of `apps/web/lib/engine-routes.ts`, from the engine's OpenAPI document."""
    lines = [f"  {json.dumps(route)}: {body};" for route, body in routes(spec).items()]
    return HEAD + "export type EngineRoutes = {\n" + "\n".join(lines) + "\n};\n"


def spec() -> dict[str, Any]:
    from engine.api.app import app

    return app.openapi()
