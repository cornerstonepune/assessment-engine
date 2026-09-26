#!/usr/bin/env python3
"""The Level 2 validator of docs/school-os-proposal-capability-behaviours.md §5, as code, so the draft's
validity is a command: python3 research/level2_validate.py docs/school-os-level2-behaviours-draft.json
Exit 0 when every stage passes; 1 otherwise, with each failure named. No model is called."""
import json, re, sys
from itertools import combinations

STAGES = ["foundational", "preparatory", "middle", "secondary"]
MODES = {"observation", "artefact", "audio", "video_clip", "rubric", "sheet", "test", "self_voice", "peer_comment", "parent_voice"}
ALLOWED = {"foundational": MODES - {"test"}, "preparatory": MODES, "middle": MODES, "secondary": MODES}
SETTINGS = {"lesson", "practice", "project", "circle", "play", "outdoors", "home"}
WORDS = {"capable", "kind", "unafraid"}
REASONS = {"no_observable_form", "capability_too_broad", "stage_unclear", "other"}
NOT_A_VERB = {"the", "a", "an", "is", "are", "has", "have", "child", "she", "he", "they", "i", "it", "this", "that", "their", "often", "always"}
FREQUENCY = {"often", "always", "usually", "consistently", "never", "regularly", "sometimes", "rarely"}
BANNED = {  # a row in the engine; here a list, grouped as the proposal groups it
    "feeling or state": ["happy", "sad", "anxious", "angry", "confident", "motivated", "bored", "upset", "scared", "afraid", "nervous", "excited", "frustrated", "shy", "enjoys", "loves", "likes", "feels", "calm"],
    "label": ["lazy", "gifted", "weak", "slow", "bright", "naughty", "hyperactive", "disruptive", "talented", "intelligent", "smart", "clever", "struggling"],
    "body": ["weight", "bmi", "fat", "thin", "height", "appearance", "overweight", "skinny"],
    "comparison": ["better than", "best", "top", "behind", "rank", "ahead of", "fastest", "cleverest", "first in class"],
    "diagnosis": ["adhd", "autism", "autistic", "dyslexia", "dyslexic", "disorder", "depression", "depressed"],
}
STOP = {"a", "an", "the", "and", "or", "of", "to", "in", "on", "for", "with", "as", "such", "at", "by", "it", "its", "their", "them", "they", "that", "this", "is", "are", "be", "when", "from", "one", "two", "without", "before", "after", "own", "not"}
ID_RE = re.compile(r"^[a-z][a-z0-9-]{3,60}$")


def toks(s):
    return {w for w in re.findall(r"[a-z']+", s.lower()) if w not in STOP}


def jaccard(a, b):
    ta, tb = toks(a), toks(b)
    return len(ta & tb) / len(ta | tb) if ta | tb else 0.0


def banned_in(text):
    low = text.lower()
    hits = []
    for group, words in BANNED.items():
        for w in words:
            if re.search(r"\b" + re.escape(w) + r"\b", low):
                hits.append(f"{w} ({group})")
    return hits


def main(path):
    doc = json.load(open(path))
    fails = []          # (check, capability, stage, detail)
    failed_stages = set()

    def fail(check, cap, stage, detail):
        fails.append((check, cap, stage, detail))
        failed_stages.add((cap, stage))

    word_count = {s: {w: 0 for w in WORDS} for s in STAGES}
    all_ids = {}
    for cap in doc["capabilities"]:
        cid = cap["capability_id"]
        stages = cap.get("stages", [])
        if [s["stage_id"] for s in stages] != STAGES:
            fail("V1", cid, "-", f"stages are {[s['stage_id'] for s in stages]}")
        prev_ids = set()
        statements = []  # (stage, id, statement)
        for s in stages:
            sid = s["stage_id"]
            bs = s.get("behaviours", [])
            if not 5 <= len(bs) <= 8:
                fail("V1", cid, sid, f"{len(bs)} behaviours")
            modes = set()
            ids_here = set()
            for b in bs:
                st, sees, ce = b["statement"], b["adult_sees"], b["counter_example"]
                if not ID_RE.match(b["id"]):
                    fail("V1", cid, sid, f"id {b['id']!r} malformed")
                if b["id"] in all_ids:
                    fail("V1", cid, sid, f"id {b['id']} repeats {all_ids[b['id']]}")
                all_ids[b["id"]] = f"{cid}/{sid}"
                ids_here.add(b["id"])
                # V2 form
                words = st.split()
                if len(words) > 25:
                    fail("V2", cid, sid, f"{b['id']}: {len(words)} words")
                first = re.sub(r"[^a-z]", "", words[0].lower()) if words else ""
                if first in NOT_A_VERB:
                    fail("V2", cid, sid, f"{b['id']}: starts with {words[0]!r}")
                if not st.endswith(".") or ". " in st:
                    fail("V2", cid, sid, f"{b['id']}: not one sentence")
                if re.search(r"\betc\b", st.lower()):
                    fail("V2", cid, sid, f"{b['id']}: 'etc'")
                freq = FREQUENCY & set(re.findall(r"[a-z]+", st.lower()))
                if freq:
                    fail("V2", cid, sid, f"{b['id']}: frequency word {sorted(freq)}")
                # V3 banned words, on every field an educator reads
                for field, text in (("statement", st), ("adult_sees", sees), ("counter_example", ce)):
                    hits = banned_in(text)
                    if hits:
                        fail("V3", cid, sid, f"{b['id']}.{field}: {hits}")
                # V4 modes and settings
                if b["capture_mode"] not in ALLOWED[sid]:
                    fail("V4", cid, sid, f"{b['id']}: mode {b['capture_mode']} not allowed at {sid}")
                modes.add(b["capture_mode"])
                if b["setting"] not in SETTINGS:
                    fail("V4", cid, sid, f"{b['id']}: setting {b['setting']}")
                # V5 grows_from
                if sid == STAGES[0] and b["grows_from"]:
                    fail("V5", cid, sid, f"{b['id']}: grows_from at first stage")
                if sid != STAGES[0] and b["grows_from"] not in prev_ids:
                    fail("V5", cid, sid, f"{b['id']}: grows_from {b['grows_from']!r} not in previous stage")
                # V6 words
                ws = set(b["words"])
                if not ws or not ws <= WORDS:
                    fail("V6", cid, sid, f"{b['id']}: words {b['words']}")
                for w in ws:
                    word_count[sid][w] += 1
                # V7 counter-example
                if re.match(r"^(does not|do not|doesn't|don't)\b", ce.lower()):
                    fail("V7", cid, sid, f"{b['id']}: counter-example is a bare negation")
                if jaccard(st, ce) >= 0.6:
                    fail("V7", cid, sid, f"{b['id']}: counter-example overlaps statement {jaccard(st, ce):.2f}")
                # V8 school's words
                for field, text in (("statement", st), ("adult_sees", sees), ("counter_example", ce)):
                    if re.search(r"\bteachers?\b", text.lower()):
                        fail("V8", cid, sid, f"{b['id']}.{field}: 'teacher'")
                statements.append((sid, b["id"], st))
            if len(modes) < 2:
                fail("V4", cid, sid, f"only {sorted(modes)} capture modes")
            prev_ids = ids_here
        # V5 duplicates across the capability
        for (s1, i1, t1), (s2, i2, t2) in combinations(statements, 2):
            j = jaccard(t1, t2)
            if j >= 0.6:
                fail("V5", cid, s2, f"{i1} and {i2} overlap {j:.2f}")
        # V9 could_not
        cn = cap.get("could_not")
        if not isinstance(cn, list):
            fail("V9", cid, "-", "could_not missing")
        else:
            for e in cn:
                if e.get("reason") not in REASONS or not e.get("detail"):
                    fail("V9", cid, "-", f"could_not entry {e}")
    # V6 coverage per stage
    for sid in STAGES:
        for w in WORDS:
            if word_count[sid][w] < 8:
                fails.append(("V6", "-", sid, f"{w} on only {word_count[sid][w]} behaviours"))
    total = sum(len(s["behaviours"]) for c in doc["capabilities"] for s in c["stages"])
    cells = len(doc["capabilities"]) * len(STAGES)
    print(f"behaviours {total} · cells {cells} · cells passing {cells - len(failed_stages)}/{cells}")
    for sid in STAGES:
        print(f"  {sid:<12} " + "  ".join(f"{w}={word_count[sid][w]}" for w in sorted(WORDS)))
    if fails:
        print(f"FAILURES {len(fails)}")
        for f in fails:
            print("  ", *f)
        return 1
    print("every stage passes V1–V9")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "docs/school-os-level2-behaviours-draft.json"))
