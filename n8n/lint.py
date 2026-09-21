"""n8n never thinks (CLAUDE.md rule 3). This refuses any exported workflow that does.

A workflow may carry: triggers, HTTP calls to the engine by URL, filters, loops, field edits,
and credential *references*. It may not carry a Code node, a language-model node, a prompt, a
marking rule, or a secret. Run: `python n8n/lint.py n8n/workflows/*.json` — exits 1 on the first
violation, prints one line per workflow otherwise.
"""
import json
import re
import sys

THINKING_NODES = {
    "n8n-nodes-base.code", "n8n-nodes-base.function", "n8n-nodes-base.functionItem",
    "n8n-nodes-base.executeCommand", "n8n-nodes-base.pythonFunction",
}
# A sticky note is documentation and a notification is a sentence for a person: neither is
# executed, so neither can hide a rule. Prose is only suspicious where it would be *acted on* —
# an HTTP body, a Set value, a node parameter that feeds a decision.
NO_LOGIC_NODES = {"n8n-nodes-base.stickyNote"}
NOTIFY_NODES = {"n8n-nodes-base.emailSend", "n8n-nodes-base.slack", "n8n-nodes-base.telegram"}
PROMPT_TELLS = re.compile(r"\b(you are|return json only|respond with json|system prompt)\b", re.I)
SECRET_TELLS = re.compile(r"(sk-[A-Za-z0-9_-]{8,}|password|secret|bearer\s+\S{8,})", re.I)
# A header that carries authentication must come from a credential, never a literal. An n8n
# expression (leading "=") is a reference, not a secret; anything else here is one in the clear.
AUTH_HEADERS = {"authorization", "x-engine-key", "x-api-key", "apikey", "api-key"}


def _strings(v):
    if isinstance(v, str):
        yield v
    elif isinstance(v, dict):
        for x in v.values():
            yield from _strings(x)
    elif isinstance(v, list):
        for x in v:
            yield from _strings(x)


def problems(wf):
    out = []
    nodes = wf["nodes"]
    for n in nodes:
        t, name = n["type"], n["name"]
        params = n.get("parameters", {})
        if t in THINKING_NODES or t.startswith("@n8n/n8n-nodes-langchain."):
            out.append(f"{name}: {t} is a thinking node — put the logic behind an engine endpoint")
        if t in NO_LOGIC_NODES:
            continue                       # documentation on the canvas; nothing executes it
        for s in _strings(params):
            if SECRET_TELLS.search(s):
                out.append(f"{name}: a parameter value looks like a secret — use a credential")
                break
        if t in NOTIFY_NODES:
            continue                       # a sentence written for a person, not for a model
        for s in _strings(params):
            if len(s) > 400 or PROMPT_TELLS.search(s):
                out.append(f"{name}: parameter text reads like a prompt or a rule ({s[:60]!r}…)")
                break
        if t == "n8n-nodes-base.httpRequest":
            if params.get("authentication") != "genericCredentialType":
                out.append(f"{name}: HTTP node must authenticate through a credential reference, not inline")
            headers = params.get("headerParameters") or {}
            for h in headers.get("parameters") or []:
                value = str(h.get("value", ""))
                if str(h.get("name", "")).lower() in AUTH_HEADERS and not value.startswith("="):
                    out.append(f"{name}: header {h['name']!r} carries a literal credential —"
                               f" use the node's credential reference instead")
    if not any(n["type"].endswith(("Trigger", "webhook")) for n in nodes):
        out.append("no trigger node")
    return out


if __name__ == "__main__":
    bad = 0
    for path in sys.argv[1:]:
        wf = json.load(open(path))
        ps = problems(wf)
        for p in ps:
            print(f"{path}: {p}")
        bad += bool(ps)
        if not ps:
            print(f"{path}: ok — {len(wf.get('nodes', []))} nodes, no thinking, no prompt text, no secrets")
    sys.exit(1 if bad else 0)
