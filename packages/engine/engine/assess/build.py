"""Build the full set: every grade × level × variant, keys, merged print packs, catalogue JSON."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

from .ladder import LEVELS, RUNGS
from .misconceptions import catalogue
from .pick import assemble
from .render import render_sheet


def build(outroot="out", grades=("G1", "G2", "G3", "G4"), variants=2, week="W1", week_label="Week __"):
    outroot = Path(outroot)
    if outroot.exists():
        shutil.rmtree(outroot)
    outroot.mkdir(parents=True)
    index = dict(week=week, grades={}, rungs=RUNGS, levels=LEVELS, misconceptions=catalogue())
    with sync_playwright() as pw:
        for g in grades:
            gdir = outroot / g
            gdir.mkdir()
            sheets = []
            for lvl in ("Lm", "L0", "Lp"):
                for v in range(1, variants + 1):
                    s = assemble(g, lvl, v, week)
                    k = render_sheet(s, gdir, week_label, pw)
                    sheets.append(
                        dict(
                            sheet_id=k["sheet_id"],
                            level=lvl,
                            variant=v,
                            pages=k["pages"],
                            n_responses=k["n_responses"],
                            n_items=len(k["items"]),
                            rungs=sorted({i["rung"] for i in k["items"]}),
                            pdf=f"{g}/{k['sheet_id']}.pdf",
                            key=f"{g}/{k['sheet_id']}.key.json",
                        )
                    )
                    print(g, lvl, v, k["sheet_id"], k["pages"], "pages", k["n_responses"], "responses")
            # print pack: one PDF per grade, all sheets in level order (a teacher hands out by her own judgment)
            pdfs = [str(gdir / f"{s['sheet_id']}.pdf") for s in sheets]
            subprocess.run(["pdfunite", *pdfs, str(gdir / f"{g}_print_pack.pdf")], check=True)
            index["grades"][g] = dict(sheets=sheets, print_pack=f"{g}/{g}_print_pack.pdf")
    (outroot / "index.json").write_text(json.dumps(index, indent=1, ensure_ascii=False), encoding="utf-8")
    return index


if __name__ == "__main__":
    build(*(sys.argv[1:2] or ["out"]))
