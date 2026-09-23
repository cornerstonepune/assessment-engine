"""A sheet: the questions one printed paper holds, and its opaque id."""

import hashlib
from dataclasses import asdict, dataclass


@dataclass
class Sheet:
    sheet_id: str  # opaque, printed as QR + short code — the level is NOT recoverable from it
    grade: str
    level: str
    variant: int
    week: str
    items: list
    title: str = ""  # what the paper practises, from data (the skill set's name); printed beside the grade

    def n_responses(self):
        return sum(len(i.responses) for i in self.items)

    def to_dict(self):
        d = asdict(self)
        return d


def _sheet_id(grade, level, variant, week):
    raw = f"{grade}|{level}|{variant}|{week}|cornerstone"
    return "CS" + hashlib.sha1(raw.encode()).hexdigest()[:6].upper()
