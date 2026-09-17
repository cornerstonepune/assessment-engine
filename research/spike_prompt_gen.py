"""Spike (2026-09-17): generate items the way the founder describes — prompt in, questions out, no
per-topic code — then check every number with code. Prints how often the model was right.

Run:  cd packages/engine && uv run python ../../research/spike_prompt_gen.py 20
Needs GEMINI_API_KEY in the repo .env. Result recorded in research/2026-09-17-prompt-generation-spike.md.
"""
import json, ssl, sys, time, urllib.request
from pathlib import Path

import certifi
from dotenv import dotenv_values

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "packages" / "engine"))
from engine.assess import misconceptions as M
from engine.assess.items import _regroup_count_sub

KEY = dotenv_values(REPO / ".env")["GEMINI_API_KEY"]
MODELS = ["gemini-3.5-flash", "gemini-3.6-flash", "gemini-2.5-flash"]  # exact pins, ordered fallback (ADR 0004)
N = int(sys.argv[1]) if len(sys.argv) > 1 else 20

# Everything from here to the prompt is data a teacher could author in a form.
seed =json.load(open(REPO / "supabase/seed/misconceptions.json"))["misconceptions"]
sub_codes = [m for m in seed if m["op"] == "-" and m["detectable_by"] == "answer_lookup"]

spec = {
    "topic": "Subtraction",
    "skill": "NUM.OPS.02 — subtracts within 1000 with exchange",
    "learning_objective": "Exchanges one hundred for ten tens, or one ten for ten ones, exactly when a column needs it.",
    "difficulty": "Hard: 3-digit minus 3-digit, EXACTLY ONE exchange, no zero digit anywhere in the top number, answer > 0.",
    "philosophy": [
        "Say 'exchange', never 'borrow'.",
        "Each item tests exactly one idea; no tricks.",
        "Word problems use contexts a 7-year-old in Pune knows: mangoes, rupees, cricket runs, school steps.",
        "Every item must be solvable in under a minute by a child who has the skill.",
    ],
    "formats": ["column", "missing_number", "word_1step"],
    "count": N,
    "misconceptions": [{"code": m["code"], "description": m["description"]} for m in sub_codes],
}

prompt = f"""You are writing a question bank for a primary school maths skill.

SPEC (JSON):
{json.dumps(spec, indent=2)}

Produce exactly {N} items as a JSON array. Each item:
{{
  "format": one of the spec formats,
  "a": top number (int), "b": number subtracted (int),
  "answer": a - b (int),
  "stem": the question text a child reads (for column: "", for missing_number: use □ for the blank, for word_1step: one sentence),
  "missing": for missing_number only — which of "a","b","answer" is blank; else null,
  "misconceptions": [ {{"code": one of the spec codes, "wrong_answer": the exact number a child with that misconception would write}} ]
     — include every spec misconception that could actually occur on these operands (at least 3).
}}
Spread formats roughly evenly. No two items may share the same (a, b). Return only the JSON array."""

# The verifier below is the only code, and none of it is about subtraction beyond the regroup counter.
def call():
    body = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"response_mime_type": "application/json", "temperature": 1.0},
    }).encode()
    ctx = ssl.create_default_context(cafile=certifi.where())
    for model in MODELS:
        for attempt in range(3):
            req = urllib.request.Request(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                data=body, headers={"Content-Type": "application/json", "x-goog-api-key": KEY})
            try:
                with urllib.request.urlopen(req, context=ctx, timeout=120) as r:
                    out = json.load(r)
                print("model used:", model)
                return json.loads(out["candidates"][0]["content"]["parts"][0]["text"])
            except urllib.error.HTTPError as e:
                if e.code not in (404, 429, 503): raise  # 404 is returned spuriously by this API under load
                time.sleep(2 * (attempt + 1))
    raise SystemExit("all models unavailable")

items = call()
print(f"model returned {len(items)} items (asked {N})")

ok_answer = ok_constraint = 0
pred_total = pred_match = pred_no_predictor = 0
dupes = len(items) - len({(i["a"], i["b"]) for i in items})
bad = []
for i in items:
    a, b = int(i["a"]), int(i["b"])
    if int(i["answer"]) == a - b: ok_answer += 1
    else: bad.append(("answer", a, b, i["answer"]))
    three = 100 <= a <= 999 and 100 <= b <= 999
    if three and "0" not in str(a) and a - b > 0 and _regroup_count_sub(a, b) == 1: ok_constraint += 1
    else: bad.append(("constraint", a, b, _regroup_count_sub(a, b)))
    truth = M.predict("-", a, b)
    for mc in i.get("misconceptions", []):
        pred_total += 1
        code = mc["code"]
        if code not in M.SUB_PREDICTORS: pred_no_predictor += 1; continue
        if truth.get(code) == int(mc["wrong_answer"]): pred_match += 1
        else: bad.append(("misconception", a, b, code, mc["wrong_answer"], truth.get(code)))

print(f"answers correct:        {ok_answer}/{len(items)}")
print(f"constraint met:         {ok_constraint}/{len(items)}  (3-digit, no zero on top, exactly one exchange)")
print(f"duplicate (a,b) pairs:  {dupes}")
print(f"misconception claims:   {pred_total}; with a code predictor: {pred_total - pred_no_predictor}; "
      f"matched predictor: {pred_match}")
fmts = {}
for i in items: fmts[i["format"]] = fmts.get(i["format"], 0) + 1
print("formats:", fmts)
if bad:
    print("\nfailures:")
    for row in bad: print("  ", row)
print("\nsample word item:", next((i["stem"] for i in items if i["format"] == "word_1step"), None))
