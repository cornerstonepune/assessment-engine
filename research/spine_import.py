#!/usr/bin/env python3
"""Imports the spine's sources into docs/spine/sources/ as JSON, so the imported layers rebuild by one command.

python3 research/spine_import.py --ncf <NCF-SE 2023 text> --elementary <NCERT elementary PDF> --secondary <NCERT secondary PDF>

- NCF-SE 2023, Part C: curricular goals (CG) and competencies (C) per subject, per stage. The text is the PDF's
  text layer (https://ncert.nic.in/pdf/NCFSE-2023-August_2023.pdf, extracted with PyMuPDF). Art and physical
  education carry two nested learning standards per stage (LS-1, the full standard; LS-2, the minimum every school
  meets from the start) whose goal numbers overlap; LS-2 rows get their own ids (`ncf.<subject>.ls2.<stage>.<code>`).
- NCERT, Learning Outcomes at the Elementary Stage (2017; https://ncert.nic.in/pdf/publication/otherpublications/tilops101.pdf)
  and at the Secondary Stage (2019; https://ncert.nic.in/pdf/publication/otherpublications/learning_outcomes.pdf):
  the right-hand "Learning Outcomes" column of each class table. Hindi, Urdu and Sanskrit sections are left out.
- The school's own learning-objective units, from supabase/seed/registry.json.
No model is called. The PDFs are not committed; pass their local paths.
"""

import argparse
import collections
import json
import re
from pathlib import Path

R = Path(__file__).resolve().parents[1]
OUT = R / "docs/spine/sources"
CHAP = {
    1: "foundational",
    2: "language",
    3: "mathematics",
    4: "science",
    5: "social-science",
    6: "art",
    7: "interdisciplinary",
    8: "physical-education",
    9: "vocational",
}
SC = {
    "foundational": "fnd",
    "language": "lang",
    "mathematics": "math",
    "science": "sci",
    "social-science": "sst",
    "art": "art",
    "world-around-us": "world",
    "individuals-in-society": "society",
    "environmental-education": "env",
    "physical-education": "pe",
    "vocational": "voc",
}
ST = {"foundational": "F", "preparatory": "P", "middle": "M", "secondary": "S"}
ART = {
    "Visual Arts": "visual",
    "Theatre": "theatre",
    "Music": "music",
    "Dance and Movement": "dance",
}
NOISE = re.compile(
    r"^(Part C|National Curriculum Framework for School Education|\d{1,3}|Table \d.*|\s*)$"
)


def ncf_rows(text_path):
    lines = Path(text_path).read_text(encoding="utf-8", errors="replace").split("\n")
    rows, cur = [], None
    chapter = sub = stage = domain = ls = None

    def flush():
        nonlocal cur
        if cur:
            cur["text"] = re.sub(r"\s+", " ", " ".join(cur.pop("buf"))).strip(" .")
            rows.append(cur)
            cur = None

    for i in range(9220, 25400):
        s = lines[i].strip()
        if m := re.match(r"^Chapter (\d+)\s*$", s):
            flush()
            chapter = int(m.group(1))
            sub = stage = domain = ls = None
            continue  # noqa: E702
        if m := re.match(r"^(\d\.\d\.\d)\s*$", s):
            flush()
            sub = m.group(1)
            ls = None
            continue  # noqa: E702
        if m := re.match(r"^Learning Standards?\s*[–-]\s*([12])\s*$", s):
            flush()
            ls = int(m.group(1))
            continue  # noqa: E702
        if m := re.match(
            r"^(?:R1 and R2 in the |R3 in the |Content for )?(Foundational|Preparatory|Middle|Secondary) Stage(?:\s*\(Grades? [0-9 and]+\))?\s*$",
            s,
        ):
            flush()
            stage = m.group(1).lower()
            continue  # noqa: E702
        if m := re.match(r"^Domain:\s*(.+)$", s):
            flush()
            domain = m.group(1).strip()
            continue  # noqa: E702
        if chapter == 6 and s in ART:
            flush()
            domain = s
            continue  # noqa: E702
        if m := re.match(r"^(CG-\d+|C-\d+\.\d+)\s*$", s):
            flush()
            cur = {
                "code": m.group(1),
                "kind": "CG" if m.group(1).startswith("CG") else "C",
                "chapter": chapter,
                "sub": sub,
                "stage": stage or ("foundational" if chapter == 1 else None),
                "domain": domain,
                "ls": ls,
                "line": i + 1,
                "buf": [],
            }
            continue
        if cur is not None:
            if NOISE.match(s):
                continue
            if re.match(r"^(Section \d|\d\.\d\s|Chapter )", s):
                flush()
                continue  # noqa: E702
            cur["buf"].append(s)
    flush()
    return rows


def ncf_competencies(text_path):
    out = []
    for e in ncf_rows(text_path):
        sub = e["sub"] or ""
        subject = CHAP.get(int(sub[0])) if sub else "foundational"
        stage, area = e["stage"], None
        if subject == "foundational":
            stage, area = "foundational", e["domain"]
        if subject == "language":
            area = {"2.4.1": "R1", "2.4.2": "R2", "2.4.3": "R3"}.get(sub)
        if subject == "art":
            area = "LS-2 (all art forms)" if e["ls"] == 2 else ART.get(e["domain"])
        if subject == "physical-education" and e["ls"] == 2:
            area = "LS-2 (minimum standard)"
        if subject == "interdisciplinary":
            subject, stage, area = {
                "7.4.2": ("world-around-us", "preparatory", None),
                "7.5.1": ("individuals-in-society", "secondary", "grade 9"),
                "7.5.2": ("environmental-education", "secondary", "grade 10"),
            }[sub]
        text = re.split(r"\s\d\.\d\.\d(?:\.\d)?\s+(?=[A-Z])", e["text"])[0]
        text = re.split(r"\sTable \d", text)[0]
        text = re.sub(r"\s*\b\d\.\d\.\d(\.\d)?\b\s*$", "", text)
        text = (
            re.sub(r"\s*(Domain:)?\s*Positive Learning Habits.*$", "", text)
            if subject == "foundational"
            else text
        )
        text = re.sub(r"languages1\b", "languages", text)
        text = re.sub(r"\s*\(from C.*$", "", text)
        parts = [
            p.strip() for p in re.split(r"\s(?=C-\d+\.\d+\s)", " " + text) if p.strip()
        ]
        base = {
            "subject": subject,
            "stage": stage,
            "area": area,
            "ls": e["ls"],
            "line": e["line"],
        }
        pieces = [(e["code"], e["kind"], parts[0])]
        if len(parts) > 1 and e["kind"] == "CG":
            pieces += [
                (m.group(1), "C", m.group(2))
                for p in parts[1:]
                if (m := re.match(r"(C-\d+\.\d+)\s+(.*)", p))
            ]
        for code, kind, t in pieces:
            out.append({**base, "code": code, "kind": kind, "text": t.strip(" .;")})
    for e in out:
        if (
            e["subject"] == "foundational"
            and e["code"].split("-")[1].split(".")[0] == "13"
        ):
            e["area"] = "Positive Learning Habits"
        ns = SC[e["subject"]]
        if e["subject"] == "language":
            ns += "." + e["area"].lower()
        elif e["subject"] == "art":
            ns += ".ls2" if e["ls"] == 2 else "." + (e["area"] or "x")
        elif e["subject"] == "physical-education" and e["ls"] == 2:
            ns += ".ls2"
        e["id"] = f"ncf.{ns}.{ST[e['stage']]}.{e['code']}"
        if e["kind"] == "C":
            e["cg"] = (
                e["id"][: -len(e["code"])]
                + "CG-"
                + e["code"].split("-")[1].split(".")[0]
            )
        if len(e["text"]) > 350:
            m = re.search(r"^(.{200,350}?[.;])\s", e["text"] + " ")
            e["text_full"], e["text"] = (
                e["text"],
                (m.group(1) if m else e["text"][:350]).rstrip(" .;"),
            )
        e.pop("ls")
    ids = collections.Counter(e["id"] for e in out)
    dups = [k for k, v in ids.items() if v > 1]
    have = set(ids)
    orphans = [e["id"] for e in out if e["kind"] == "C" and e["cg"] not in have]
    assert not dups, f"duplicate ids: {dups[:8]}"
    assert not orphans, f"competencies without a goal: {orphans[:8]}"
    return out


ROM = {
    "I": 1,
    "II": 2,
    "III": 3,
    "IV": 4,
    "V": 5,
    "VI": 6,
    "VII": 7,
    "VIII": 8,
    "IX": 9,
    "X": 10,
}


def _right_column(page):
    w = page.rect.width
    blocks = sorted(
        (b[1], b[4]) for b in page.get_text("blocks") if b[0] >= w * 0.5 - 5
    )
    return "\n".join(t for _, t in blocks)


def _items(text, bullet):
    text = re.sub(
        r"(?m)^\s*(Learning Outcomes.*|Suggested Pedagogical Processes|The learners?\s*[—­-]*\s*|\d{1,3})\s*$",
        "",
        text,
    )
    text = re.sub(
        r"Learning Outcomes Part \d Folder\.indd.*|\d\d-\d\d-\d{4}\s+\d\d:\d\d:\d\d",
        "",
        text,
    )
    items = []
    for p in re.split(bullet, text)[1:]:
        p = re.sub(r"\s*\n\s*", " ", p).strip()
        p = re.sub(r"\s*[–-]\s*[–-]\s*", " – ", p)
        p = re.sub(r"\s*[\uf000-\uf8ff]\s*", " – ", p)
        p = re.sub(r"\s{2,}", " ", p)
        if len(p) > 12:
            items.append(p)
    return items


def ncert_outcomes(elementary, secondary):
    import pymupdf

    rows, cur = [], None
    key = [
        ("math", "math"),
        ("evs", "evs"),
        ("environmental", "evs"),
        ("social", "sst"),
        ("science", "sci"),
        ("english", "eng"),
    ]
    for pno, page in enumerate(pymupdf.open(elementary)):
        full = page.get_text()
        for m in re.finditer(r"Class\s+([IVX]+)\s*\(([^)]+)\)", full):
            subj = next((v for k, v in key if k in m.group(2).lower()), None)
            if subj and m.group(1) in ROM:
                cur = (subj, ROM[m.group(1)])
                break
        if cur and ("Learning Outcomes" in full or "learner" in full):
            rows += [
                {
                    "subject": cur[0],
                    "class": cur[1],
                    "text": t,
                    "page": pno + 1,
                    "src": "NCERT, Learning Outcomes at the Elementary Stage (2017)",
                }
                for t in _items(_right_column(page), r"\n\s*•\s*")
            ]
    doc = pymupdf.open(secondary)
    ranges = [
        ("eng", 29, 56),
        ("sci", 57, 67),
        ("sst", 68, 92),
        ("math", 93, 99),
        ("hpe", 100, 108),
        ("art", 109, len(doc)),
    ]
    cls = area = None
    for pno, page in enumerate(doc):
        n = pno + 1
        subj = next((s for s, a, b in ranges if a <= n <= b), None)
        if not subj:
            continue
        full = page.get_text()
        if m := re.search(r"^\s*Class (IX|X)\b(?:\s*\(([^)]+)\))?", full, re.M):
            cls = ROM[m.group(1)]
            area = (m.group(2) or area) if subj == "art" else None
        if n in (29, 57, 68, 93, 100):
            cls = 9
        if "Learning Outcomes" in full or "learner" in full:
            rows += [
                {
                    "subject": subj,
                    "class": cls,
                    "area": area,
                    "text": t,
                    "page": n,
                    "src": "NCERT, Learning Outcomes at the Secondary Stage (2019)",
                }
                for t in _items(_right_column(page), r"\n\s*y\s+")
            ]
    out, cnt = [], collections.Counter()
    for r in rows:
        if re.search(r"[\u0900-\u097F]", r["text"]) or r["class"] is None:
            continue
        cnt[(r["subject"], r["class"])] += 1
        r["id"] = (
            f"ncert.{r['subject']}.{r['class']}.{cnt[(r['subject'], r['class'])]:02d}"
        )
        out.append(r)
    return out


def school_units():
    reg = json.load(open(R / "supabase/seed/registry.json"))
    units = collections.OrderedDict()
    for x in reg["learning_objectives"]:
        u = units.setdefault(
            (x["subject"], x["unit"]),
            {
                "subject": x["subject"],
                "unit": x["unit"],
                "bands": set(),
                "n": 0,
                "samples": [],
            },
        )
        u["bands"].add(x["band"])
        u["n"] += 1
        if len(u["samples"]) < 3:
            u["samples"].append(x["title"])
    out = []
    for i, u in enumerate(units.values()):
        u["bands"], u["id"] = sorted(u["bands"]), f"unit.{i + 1:03d}"
        out.append(u)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ncf", required=True)
    ap.add_argument("--elementary", required=True)
    ap.add_argument("--secondary", required=True)
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    ncf = ncf_competencies(a.ncf)
    lo = ncert_outcomes(a.elementary, a.secondary)
    units = school_units()
    for name, data in (
        ("ncf_se_2023_competencies.json", ncf),
        ("ncert_learning_outcomes.json", lo),
        ("school_units.json", units),
    ):
        (OUT / name).write_text(json.dumps(data, indent=0, ensure_ascii=False))
    print(
        f"NCF-SE rows {len(ncf)} (goals {sum(e['kind'] == 'CG' for e in ncf)}, competencies {sum(e['kind'] == 'C' for e in ncf)}) · NCERT outcomes {len(lo)} · school units {len(units)}"
    )
    print("  by subject:", dict(collections.Counter(e["subject"] for e in ncf)))


if __name__ == "__main__":
    main()
