"""The likely wrong answers of every English sample (research/english_check.py): each one names a mistake of its skill,
is a wrong answer the question could really get, and, where the mistake follows a rule, is the answer that rule gives.

A sample's `wrong` is {what the child writes: mistake code}. What "could really get" means depends on the kind:
a choice is one of the printed options; an order is every item, once, in another order ("a, b, c"); a match is a
pair the key does not make ("left - right"); a sort puts an item in a group it does not belong to ("item: group");
a table box holds what the key does not ("label: value"); marked or copied words are in the text; punctuating keeps
the words. Where the mistake is a rule (the final e kept before -ing, -s where the word needs -es, the printed order
kept), code works the wrong answer out again from the sample's own inputs and it must match.
"""

import english_rules as er

OPEN = {"ENG.SHORT_ANSWER", "ENG.REWRITE", "ENG.SHORT_WRITE"}


def _orders(ans):
    """The neighbour swaps of an order: the answer with one pair of neighbours exchanged."""
    return [ans[:i] + [ans[i + 1], ans[i]] + ans[i + 2 :] for i in range(len(ans) - 1)]


def _first_letter_order(items):
    return sorted(items, key=lambda w: w[:1].lower())  # stable: words sharing a first letter keep the printed order


def _short_last(items):
    """Dictionary order, except a word that starts another goes after it (peach before pea)."""
    out = sorted(items, key=str.lower)
    for i in range(len(out) - 1):
        if out[i + 1].lower().startswith(out[i].lower()):
            out[i], out[i + 1] = out[i + 1], out[i]
    return out


def reproduce(code, s):
    """The wrong answers a rule-shaped mistake gives on this sample, or None where the mistake has no rule here."""
    c, ans, opts = s.get("check") or {}, s.get("answer"), s.get("options")
    kind, base = c.get("compute"), (c.get("base") or "").lower()
    end = c.get("ending")
    if kind == "add_ending":
        stem = base[:-1] if base.endswith("e") and end == "ing" else base
        return {
            "M_ENG_E_KEPT": {base + end, base + ("d" if end == "ed" and base.endswith("e") else end)} if base.endswith("e") else None,
            "M_ENG_NO_DOUBLE": {stem + end} if er.doubles(base, c.get("stress_last", False)) else None,
            "M_ENG_Y_KEPT": {base + end, base + ("es" if end == "s" else end)} if base.endswith("y") else None,
            "M_ENG_ES_MISSED": {base + "s"} if end == "s" else None,
            "M_ENG_IRREG_ADDS_ED": {er.add_ending(base, "ed"), base + "ed"} if end == "ed" else None,
            "M_ENG_TENSE_IRREGULAR_ED": {er.add_ending(base, "ed"), base + "ed"} if end == "ed" else None,
        }.get(code)
    if kind == "irregular_past":
        if code in ("M_ENG_IRREG_ADDS_ED", "M_ENG_TENSE_IRREGULAR_ED"):
            return {er.add_ending(base, "ed"), base + "ed", base + "d"}
        return None
    if kind == "plural":
        return {
            "M_ENG_ES_MISSED": {base + "s"},
            "M_ENG_O_ES_MISSED": {base + "s"} if base.endswith("o") else None,
            "M_ENG_Y_KEPT": {base + "s"} if base.endswith("y") else None,
            "M_ENG_Y_CHANGED_AFTER_VOWEL": {base[:-1] + "ies", base[:-2] + "ies"} if base.endswith("y") else None,
        }.get(code)
    if kind == "affix":
        root, suf, pre = (c.get("root") or "").lower(), (c.get("suffix") or "").strip("-").lower(), c.get("prefix")
        if pre:
            return None
        return {
            "M_ENG_E_KEPT": {root + suf} if root.endswith("e") else None,
            "M_ENG_E_DROPPED_EARLY": {root[:-1] + suf} if root.endswith("e") else None,
            "M_ENG_Y_KEPT": {root + suf} if root.endswith("y") else None,
        }.get(code)
    if kind == "compound":
        parts = [p.lower() for p in c.get("parts", [])]
        return {"M_ENG_COMPOUND_SPACE": {" ".join(parts), "-".join(parts)}}.get(code)
    if kind == "contraction" and isinstance(ans, str):
        full = er.plain(c.get("full", "")).split()
        bare = er.plain(ans).replace("'", "")
        return {
            "M_ENG_APOS_MISSING": {bare},
            "M_ENG_APOS_PLACE": {full[0] + "'nt"} if len(full) == 2 and full[1] == "not" else None,
            "M_ENG_APOS_KEPT_LETTERS": {full[0] + "'" + full[1]} if len(full) == 2 else None,
        }.get(code)
    if kind == "possessive":
        owner = c.get("owner", "")
        right = er.possessive(owner, c.get("many", False))
        return {
            "M_ENG_POSS_NO_APOSTROPHE": {er.plain(right).replace("'", "")},
            "M_ENG_POSS_WRONG_PLACE": {er.plain(x) for x in (owner + "'", owner + "'s", owner[:-1] + "'s", owner + "s'")} - {er.plain(right)},
            "M_ENG_POSS_PLURAL_S_S": {er.plain(owner + "'s")} if owner.endswith("s") else None,
            "M_ENG_POSS_IRREGULAR": {er.plain(owner + "s'"), er.plain(owner + "s")} if not owner.endswith("s") else None,
        }.get(code)
    if isinstance(ans, list) and isinstance(opts, list):
        printed = {", ".join(opts)}
        swaps = {", ".join(o) for o in _orders(ans)}
        return {
            "M_ENG_ALPHA_FIRST_ONLY": {", ".join(_first_letter_order(opts))} | printed,
            "M_ENG_ALPHA_SHORT_LAST": {", ".join(_short_last(opts))},
            "M_ENG_ORDER_AS_PRINTED": printed,
            "M_ENG_STAGE_TEXT_ORDER": printed,
            "M_ENG_STEP_ORDER": printed,
            "M_ENG_SHADES_REVERSED": {", ".join(reversed(ans))},
            "M_ENG_ORDER_SWAP": swaps,
            "M_ENG_SHADES_MIDDLE_SWAPPED": swaps,
        }.get(code)
    return None


def check(s, mistakes):
    """(faults, checks run) for the wrong answers of one sample."""
    f, ran = [], {}
    q, ans, opts, text = s["question_type"], s.get("answer"), s.get("options"), s.get("text") or ""
    wrong = s.get("wrong") or {}
    if not wrong:
        return ["no likely wrong answer, each tied to a named mistake"], ran
    accepted = {er.plain(x) for x in [str(ans)] + list(s.get("accept") or []) if isinstance(x, str)}
    for w, code in wrong.items():
        ran["wrong answer names a mistake of its skill"] = ran.get("wrong answer names a mistake of its skill", 0) + 1
        if code not in mistakes:
            f.append(f"wrong answer {w!r} names {code}, not a mistake of this skill")
        if er.plain(w) in accepted:
            f.append(f"wrong answer {w!r} is a right answer")
        fit = fits(q, w, s, ans, opts, text)
        if fit:
            f.append(f"wrong answer {w!r}: {fit}")
        else:
            ran[f"wrong answer fits {q}"] = ran.get(f"wrong answer fits {q}", 0) + 1
        want = reproduce(code, s)
        if want is not None:
            if er.plain(w) not in {er.plain(x) for x in want}:
                f.append(f"wrong answer {w!r}: {code} gives {sorted(want)}, not this")
            else:
                ran["wrong answer reproduced from its mistake"] = ran.get("wrong answer reproduced from its mistake", 0) + 1
    return f, ran


def fits(q, w, s, ans, opts, text):
    """Why a wrong answer cannot be one this question gets, or '' if it can."""
    p = s.get("_passage_text", "")
    if q == "ENG.CHOOSE" or (q == "ENG.GAP" and opts):
        return "" if w in opts else "is not one of the printed options"
    if q == "ENG.ORDER":
        if not _is_order(w, opts or []):
            return "is not every item once, joined by ', '"
        return "is the key's order" if w == ", ".join(ans) else ""
    if q == "ENG.MATCH":
        left, right = (opts or {}).get("left", []), (opts or {}).get("right", [])
        pairs = [(a, b) for a in left for b in right if w == f"{a} - {b}"]
        if not pairs:
            return "is not 'left - right' made of the printed items"
        return "is a pair the key makes" if list(pairs[0]) in [list(x) for x in ans] else ""
    if q == "ENG.SORT":
        hits = [(i, g) for i in opts or [] for g in (ans or {}) if er.plain(w) == er.plain(f"{i}: {g}")]
        if not hits:
            return "is not 'item: group' made of a printed item and a group"
        return "puts the item where the key puts it" if hits[0][0] in ans[hits[0][1]] else ""
    if q == "ENG.TABLE":
        hits = [k for k in (ans or {}) if er.plain(w).startswith(er.plain(f"{k}: "))]
        if not hits:
            return "is not 'box: what the child writes' for a box of the table"
        return "is what the key puts in the box" if er.plain(w[len(hits[0]) + 2 :]) == er.plain(ans[hits[0]]) else ""
    if q == "ENG.MARK_WORDS":
        parts = [x.strip() for x in w.split(",") if x.strip()]
        if not parts or not all(er.found(x, text or p) for x in parts):
            return "marks words that are not in the text"
        return "marks exactly the key's words" if sorted(map(er.plain, parts)) == sorted(map(er.plain, ans)) else ""
    if q == "ENG.COPY":
        return "" if er.found(w, p) else "is not copied from the passage"
    if q == "ENG.PUNCTUATE":
        return "" if er.same_words(text, w) else "changes the words instead of the punctuation"
    if q in OPEN:
        return "" if len(er.words(w)) >= 1 else "is empty"
    return ""


def _is_order(w, items):
    """w is every item once, joined by ', ' (items may hold commas, so they are matched, not split)."""
    left, rest = list(items), w
    while left:
        hit = next((i for i in sorted(left, key=len, reverse=True) if rest == i or rest.startswith(i + ", ")), None)
        if hit is None:
            return False
        left.remove(hit)
        rest = rest[len(hit) + 2 :] if len(rest) > len(hit) else ""
    return rest == ""

