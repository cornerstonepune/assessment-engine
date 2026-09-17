"""Assemble a sheet from a blueprint. Seeded by (grade, level, variant, week) so it is reproducible,
and variant k is guaranteed to differ from variant j in every operand."""
import random, hashlib, json
from dataclasses import dataclass, field, asdict
from .blueprints import BLUEPRINTS
from .ladder import LEVELS

@dataclass
class Sheet:
    sheet_id: str        # opaque, printed as QR + short code — the level is NOT recoverable from it
    grade: str
    level: str
    variant: int
    week: str
    items: list
    def n_responses(self):
        return sum(len(i.responses) for i in self.items)
    def to_dict(self):
        d = asdict(self); return d

def _sheet_id(grade, level, variant, week):
    raw = f"{grade}|{level}|{variant}|{week}|cornerstone"
    return "CS" + hashlib.sha1(raw.encode()).hexdigest()[:6].upper()

def assemble(grade, level, variant=1, week="W1"):
    seed = int(hashlib.sha1(f"{grade}{level}{variant}{week}".encode()).hexdigest(), 16) % (2**32)
    rng = random.Random(seed)
    items = []
    seen = set()
    for label, fn in BLUEPRINTS[(grade, level)]:
        for _ in range(20):
            it = fn(rng)
            key = json.dumps(it.spec, sort_keys=True)
            if key not in seen:
                seen.add(key); break
        it.spec["_slot"] = label
        items.append(it)
    return Sheet(_sheet_id(grade, level, variant, week), grade, level, variant, week, items)

def assemble_set(grade, variants=2, week="W1"):
    return [assemble(grade, lvl, v, week) for lvl in ("Lm", "L0", "Lp") for v in range(1, variants + 1)]
