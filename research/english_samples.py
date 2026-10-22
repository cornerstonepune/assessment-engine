"""The checks on every worked example of the English foundation (research/english_check.py): its shape for its
question type, its level's rule, the answer worked out again by code where a rule gives it (english_rules.py), and
that none of it is Cambridge's own text. Returns the faults and how many checks code ran, by kind.
"""

import re
from collections import Counter

import english_rules as er
import english_wrong

GAP = "___"
# what a question type's example must carry, beyond a skill, a level, an ask and an answer
JUDGED = {"ENG.SHORT_ANSWER", "ENG.REWRITE", "ENG.SHORT_WRITE"}


def check(t, levels, used, objs, pdf_text):
    import english_check as ec

    faults, ran = [], Counter()
    skills = {s["code"]: s for s in t["skill"]}
    passages = {p["code"]: p for p in t["passage"]}
    rubrics = {r["code"]: r for r in t["rubric"]}
    order, _ = ec.vocabulary()
    by_level, seen = {}, {}
    cambridge = ec.shingles(pdf_text, ec.SHINGLE)
    eg = examples_given(objs)
    for p in t["passage"]:
        if not p.get("text", "").strip() or p.get("grade") not in {s["grade"] for s in skills.values()}:
            faults.append(f"passage {p['code']}: needs text and a grade")
    for s in t["skill_level_sample"]:
        key = (s["skill_code"], s["difficulty"])
        label = f"{s['skill_code']} {s['difficulty']} {s['question_type']} #{s.get('n')}"
        by_level.setdefault((*key, s["question_type"]), []).append(s.get("n"))
        skill, level = skills.get(s["skill_code"]), levels.get(key)
        if not skill or not level:
            faults.append(f"{label}: no such skill or level")
            continue
        passage = passages.get(s.get("passage")) if s.get("passage") else None
        if s.get("passage") and (not passage or passage["grade"] != skill["grade"]):
            faults.append(f"{label}: passage {s.get('passage')} missing or of another grade")
        f, n = one(s, skill, level, passage, rubrics, used.get(s["skill_code"], []))
        faults += [f"{label}: {x}" for x in f]
        ran.update(n)
        sig = er.plain(" ".join([s.get("text") or "", str(s.get("answer")), s.get("passage") or "", s.get("ask") or ""]))
        if sig in seen:
            faults.append(f"{label}: the same example as {seen[sig]}")
        seen[sig] = label
        texts = ec.example_texts(s, passages)
        for x in texts:
            if bad := {w for w in er.words(x) if w.lower() in ec.AMERICAN}:
                faults.append(f"{label}: American spelling {sorted(bad)}")
        if hit := ec.shingles(" ".join(texts), ec.SHINGLE) & cambridge:
            faults.append(f"{label}: shares Cambridge's words: {sorted(hit)[:2]}")
        ran["not Cambridge's words"] += 1
        given = {w for c in skill["objectives"] for w in eg.get(c, ())}
        targets = {er.plain(w) for w in ec.flat(s.get("answer")) + ec.flat(s.get("options")) + (s.get("accept") or [])}
        if hit := targets & given:
            faults.append(f"{label}: uses Cambridge's own example {sorted(hit)} for {skill['objectives']}")
        ran["not Cambridge's examples"] += 1
    for key in levels:
        if not any(k[:2] == key for k in by_level):
            faults.append(f"{key[0]} {key[1]}: needs examples 1, 2 and 3 of each kind it uses, has none")
    for key, ns in by_level.items():
        if sorted(ns, key=str) != [1, 2, 3]:
            faults.append(f"{key[0]} {key[1]}: needs examples 1, 2 and 3 of {key[2]}, has {ns}")
    for code, skill in skills.items():
        kinds = {s["question_type"] for s in t["skill_level_sample"] if s["skill_code"] == code}
        if missing := set(skill["question_types"]) - kinds:
            faults.append(f"{code}: question types {sorted(missing)} have no example")
    for p in t["passage"]:
        if hit := ec.shingles(p["text"], ec.SHINGLE) & cambridge:
            faults.append(f"passage {p['code']}: shares Cambridge's words: {sorted(hit)[:2]}")
    long = ec.shingles(pdf_text, ec.LONG_SHINGLE)
    ours = [(s["code"], s["learning_objective"] + " " + s["name"]) for s in t["skill"]]
    ours += [(f"{lv['skill_code']} {lv['difficulty']}", lv["looks_like"]) for lv in t["skill_level"]]
    ours += [(n["objective"], n["why"] + " " + n["observe"]) for n in t["not_on_paper"]]
    for label, text in ours:
        if hit := ec.shingles(text, ec.LONG_SHINGLE) & long:
            faults.append(f"{label}: copies Cambridge's words: {sorted(hit)[:2]}")
    return faults, ran


def examples_given(objs):
    """Cambridge's own examples, the words after "e.g." in each objective: an example of ours never uses them."""
    out = {}
    for code, o in objs.items():
        text = o["words"]
        for m in re.finditer(r"e\.g\.", text):
            depth, end = text[: m.start()].count("(") - text[: m.start()].count(")"), len(text)
            if depth > 0:  # inside brackets: up to the bracket that closes them, nested ones included
                level = depth
                for i in range(m.end(), len(text)):
                    level += {"(": 1, ")": -1}.get(text[i], 0)
                    if level < depth:
                        end = i
                        break
            clause = re.sub(r"\([^()]*\)", " ", text[m.end() : end])
            parts = re.split(r"[,;:…]|\band\b|\binstead of\b|\.\.\.", clause)
            ws = {er.plain(w).strip(" .'\"") for w in parts}
            out[code] = out.get(code, set()) | {w for w in ws if len(w) > 2}
    return out


def one(s, skill, level, passage, rubrics, mistakes):
    """(faults, checks run) for one example."""
    f, ran = [], Counter()
    q, ans, opts, text = s["question_type"], s.get("answer"), s.get("options"), s.get("text") or ""
    p = (passage or {}).get("text", "")
    if q not in skill["question_types"]:
        f.append(f"{q} is not one of the skill's question types")
    if not s.get("ask", "").strip() or ans in (None, "", [], {}):
        f.append("needs an ask and an answer")
        return f, ran
    wf, wn = english_wrong.check(dict(s, _passage_text=p), mistakes)
    f += wf
    ran.update(wn)
    f += shape(q, s, ans, opts, text, p)
    ran[f"shape of {q}"] += 1
    if q in JUDGED:
        r = rubrics.get(s.get("rubric"))
        if not r or skill["code"] not in r["skill_codes"] or not s.get("key_points"):
            f.append("a judged answer needs a rubric for this skill and the key points a marker looks for")
        for w in s.get("must_contain") or []:
            if not er.found(w, str(ans)):
                f.append(f"the model answer lacks {w!r}, which the question asks for")
            ran["asked-for word in the model answer"] += 1
    rf, rn = rule(level["rule"], s, ans, opts, text, p)
    f += rf
    ran.update(rn)
    cf, cn = compute(s.get("check") or {}, s, ans, opts, text, p)
    return f + cf, ran + cn


def shape(q, s, ans, opts, text, p):
    f = []
    if q == "ENG.CHOOSE":
        if not isinstance(opts, list) or len(opts) < 2 or len(set(map(er.plain, opts))) != len(opts):
            f.append("a choice needs two or more different options")
        elif ans not in opts:
            f.append(f"the answer {ans!r} is not an option")
    elif q == "ENG.MATCH":
        left, right = (opts or {}).get("left", []), (opts or {}).get("right", [])
        if sorted(a for a, _ in ans) != sorted(left) or not all(b in right for _, b in ans):
            f.append("a match pairs every left item with one right item")
    elif q == "ENG.ORDER":
        if not isinstance(ans, list) or sorted(ans) != sorted(opts or []):
            f.append("an order is every option, once")
    elif q == "ENG.SORT":
        got = [i for v in (ans or {}).values() for i in v] if isinstance(ans, dict) else None
        if got is None or sorted(got) != sorted(opts or []):
            f.append("a sort puts every option in exactly one group")
    elif q == "ENG.GAP":
        if GAP not in text:
            f.append(f"a gap question needs {GAP} in its text")
        if opts and ans not in opts:
            f.append(f"the answer {ans!r} is not in the word bank")
    elif q == "ENG.WRITE_WORD":
        if not isinstance(ans, str) or len(ans.split()) > 2:
            f.append("a written word is one word (or two, for a short form)")
    elif q == "ENG.MARK_WORDS":
        if not isinstance(ans, list) or not all(er.found(w, text or p) for w in ans):
            f.append("the words to mark must be in the text")
    elif q == "ENG.COPY":
        if not p or not all(er.found(w, p) for w in er_list(ans)):
            f.append("copied words must be in the passage")
    elif q == "ENG.PUNCTUATE":
        if not er.same_words(text, ans) or not re.search(r"[.?!][\"”']?$", ans.strip()):
            f.append("punctuating keeps the words and ends the sentence")
    elif q == "ENG.CORRECT":
        if er.plain(text) == er.plain(ans):
            f.append("a correction changes something")
    elif q == "ENG.TABLE":
        if not isinstance(ans, dict) or not ans:
            f.append("a table's answer is its boxes, {label: what goes in it}")
    return f


def er_list(ans):
    return ans if isinstance(ans, list) else [ans] if isinstance(ans, str) else [v for v in ans.values()]


def rule(r, s, ans, opts, text, p):
    """The level's rule, applied to this example."""
    import english_check as ec

    f, ran = [], Counter()

    def within(name, value, rng):
        ran[name] += 1
        if not rng[0] <= value <= rng[1]:
            f.append(f"{name} is {value}, the level says {rng[0]}-{rng[1]}")

    targets = [x for x in ec.flat(list(ans.values()) if isinstance(ans, dict) else ans) if isinstance(x, str)]
    if "passage_words" in r:
        within("passage words", len(er.words(p)), r["passage_words"])
    if "text_words" in r:
        within("text words", len(er.words(text)), r["text_words"])
    if "answer_letters" in r:
        for w in targets:
            within("answer letters", len(er.letters(w)), r["answer_letters"])
    if "answer_words" in r:
        within("answer words", len(er.words(" ".join(targets))), r["answer_words"])
    if "options" in r and s["question_type"] in ("ENG.CHOOSE", "ENG.GAP") and opts:
        within("options", len(opts), [r["options"], r["options"]])
    if "items" in r and isinstance(opts, list):
        within("items", len(opts), r["items"])
    if "pattern" in r:
        ran["spelling pattern present"] += 1
        for w in targets if s["question_type"] not in JUDGED else []:
            if not re.search(r["pattern"], er.plain(w)):
                f.append(f"{w!r} does not show the level's pattern {r['pattern']}")
    if "answer_from" in r:
        ran["answer from the level's list"] += 1
        allowed = {er.plain(x) for x in r["answer_from"]}
        if not any(er.plain(w) in allowed or any(re.search(rf"\b{re.escape(a)}\b", er.plain(w)) for a in allowed) for w in targets):
            f.append(f"the answer uses none of the level's words {r['answer_from']}")
    if r.get("answer_in_passage"):
        ran["answer in the passage"] += 1
        if not p or not all(er.found(w, p) for w in targets):
            f.append("the answer is not in the passage")
    if "errors" in r and s["question_type"] == "ENG.CORRECT":
        within("mistakes to correct", er.corrections(text, ans), r["errors"])
    if "marks" in r and s["question_type"] == "ENG.PUNCTUATE":
        ran["marks present"] += 1
        if missing := [m for m in r["marks"] if m not in ans]:
            f.append(f"the punctuated answer lacks {missing}")
    return f, ran


def compute(c, s, ans, opts, text, p):
    """The answer worked out again from the example's inputs, by the rule it practises."""
    f, ran = [], Counter()
    kind = c.get("compute")
    if not kind:
        return f, ran
    ran[f"answer recomputed: {kind}"] += 1
    if c.get("irregular"):
        ran["answer recomputed: irregular, listed"] += 1
        return f, ran
    want = None
    if kind == "add_ending":
        want = er.add_ending(c["base"], c["ending"], c.get("stress_last", False))
    elif kind == "plural":
        want = er.plural(c["base"], c.get("f_to_ves", False), c.get("o_es", False))
    elif kind == "possessive":
        want = er.possessive(c["owner"], c.get("many", False))
    elif kind == "affix":
        want = er.affix(c["root"], c.get("prefix"), c.get("suffix"))
    elif kind == "compound":
        want = "".join(c["parts"])
    elif kind == "split":
        if er.letters("".join(ans)) != er.letters(text):
            f.append(f"the parts {ans} do not make {text!r}")
    elif kind == "contraction":
        if not er.contraction_fits(ans, c["full"]):
            f.append(f"{ans!r} is not a short form of {c['full']!r}")
    elif kind == "irregular_past":
        if er.plain(ans) in (er.add_ending(c["base"], "ed"), c["base"] + "ed"):
            f.append(f"{ans!r} is the regular past of {c['base']!r}, not an irregular one")
    elif kind == "alphabetical":
        ordered, deep = er.alphabetical(opts)
        want = ordered
        if "alpha_depth" in c and not c["alpha_depth"][0] <= deep <= c["alpha_depth"][1]:
            f.append(f"ordering needs letter {deep}, the level says {c['alpha_depth']}")
    elif kind == "passage_order":
        want = er.passage_order(opts, p)
        if want is None:
            f.append("an event to order is not in the passage word for word")
    elif kind == "index_lookup":
        want = er.index_pages(p).get(er.plain(c["entry"]))
        if want is None:
            f.append(f"{c['entry']!r} is not a line of the index or contents")
    elif kind == "alliteration":
        if not er.alliterates(" ".join(er_list(ans)), c.get("at_least", 2)):
            f.append(f"{ans!r} does not alliterate")
    elif kind == "simile":
        if not er.simile(" ".join(er_list(ans))):
            f.append(f"{ans!r} is not a simile with like or as … as")
    elif kind == "narration":
        if er.narration(p) != c["person"]:
            f.append(f"the passage is told in the {er.narration(p)} person, the key says {c['person']}")
    elif kind == "sort_pattern":
        for group, items in ans.items():
            for i in items:
                if not re.search(c["groups"][group], er.plain(i)):
                    f.append(f"{i!r} does not fit its group {group!r} ({c['groups'][group]})")
    elif kind == "odd_one_out":
        misfits = [o for o in opts if not re.search(c["pattern"], er.plain(o))]
        if misfits != [ans]:
            f.append(f"the words breaking {c['pattern']} are {misfits}, the key says {ans!r}")
    else:
        f.append(f"no computation called {kind!r}")
    if want is not None and (er.plain(want) if isinstance(want, str) else [er.plain(w) for w in want]) != (
        er.plain(ans) if isinstance(ans, str) else [er.plain(w) for w in ans]
    ):
        f.append(f"the rule gives {want!r}, the key says {ans!r}")
    return f, ran
