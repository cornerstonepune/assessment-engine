"""How a printed page looks: its CSS, and what each layout a paper has printed in draws differently from it
(`render.layouts`, goals/s18-read-as-printed.yaml). Pure: strings only."""

import re

CSS = """
@page { size: A4; margin: 0; }
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; background: #fff; color: #111; font-family: "DejaVu Sans", Arial, sans-serif; font-size: 11.5pt; line-height: 1.35; -webkit-print-color-adjust: exact; }
.page { position: relative; width: 210mm; height: 297mm; overflow: hidden; page-break-after: always; }
.page:last-child { page-break-after: auto; }
.fid { position: absolute; width: 7mm; height: 7mm; background: #000; }
.fid.tl { left: 6mm; top: 6mm; } .fid.tr { right: 6mm; top: 6mm; } .fid.bl { left: 6mm; bottom: 6mm; } .fid.br { right: 6mm; bottom: 6mm; }
.qr { position: absolute; right: 16mm; top: 15mm; width: 17mm; height: 17mm; }
.qr img { width: 100%; height: 100%; display: block; }
.code { position: absolute; right: 16mm; top: 32.5mm; width: 17mm; text-align: center; font-family: "DejaVu Sans Mono", monospace; font-size: 7.5pt; letter-spacing: .04em; }
.content { position: absolute; left: 16mm; right: 16mm; top: 15mm; bottom: 15mm; }
.head { padding-right: 22mm; border-bottom: 1.2px solid #111; padding-bottom: 2.5mm; margin-bottom: 3.5mm; }
.school { font-size: 8pt; letter-spacing: .14em; text-transform: uppercase; color: #333; }
.title { font-size: 15pt; font-weight: bold; margin-top: 1mm; }
.sub { font-size: 9.5pt; color: #333; }
.nameline { display: flex; gap: 8mm; margin-top: 3mm; font-size: 10pt; }
.nameline span { flex: 1; border-bottom: 1px solid #111; padding-bottom: 1mm; white-space: nowrap; }
.nameline span.short { flex: 0 0 34mm; }
.instr { font-size: 9pt; background: #f1f1f1; padding: 1.5mm 2.5mm; margin-bottom: 3.5mm; }
.slim { font-size: 8.5pt; color: #333; border-bottom: 1px solid #111; padding-bottom: 1.5mm; margin-bottom: 3mm; padding-right: 22mm; }
.foot { position: absolute; left: 16mm; right: 16mm; bottom: 8mm; font-size: 8pt; color: #444; display: flex; justify-content: space-between; }
.item { break-inside: avoid; margin-bottom: 4.2mm; }
.rowgroup { display: flex; gap: 4mm; align-items: flex-start; margin-bottom: 2mm; }
.rowgroup .item { flex: 1 1 0; min-width: 0; }
.rowgroup .item .work { min-height: 12mm; }
.item .q { display: flex; gap: 2.5mm; align-items: baseline; }
.item .n { font-weight: bold; width: 6mm; flex: none; }
.item .stem { font-weight: 600; }
.item .body { margin-left: 8.5mm; margin-top: 1.5mm; }
.cells { display: inline-flex; gap: 0; vertical-align: middle; }
.cell { display: inline-block; width: 8.4mm; height: 10mm; border: 1px solid #111; margin-right: -1px; background: #fff; }
.cell.sm { width: 5.4mm; height: 6.4mm; border-color: #666; }
.cells.big .cell { width: 11mm; height: 13mm; }
.work { border: 1px dashed #888; border-radius: 1.5mm; min-height: 14mm; margin-top: 1.5mm; padding: 1mm 2mm; font-size: 8pt; color: #888; }
.work.h2 { min-height: 20mm; } .work.h3 { min-height: 26mm; } .work.h4 { min-height: 34mm; }
.row { display: flex; gap: 8mm; align-items: flex-end; flex-wrap: wrap; }
.lab { font-size: 9pt; color: #333; margin-right: 2mm; }
.eq { font-size: 13pt; }
.textbox { border: 1px solid #999; border-radius: 1mm; min-height: 16mm; margin-top: 1.5mm; background: repeating-linear-gradient(#fff 0 7.5mm, #ddd 7.5mm 7.6mm); }
.tick { display: inline-block; width: 6mm; height: 6mm; border: 1px solid #111; vertical-align: middle; margin-right: 2mm; }
.tickopt { display: inline-flex; align-items: center; margin-right: 8mm; font-size: 10pt; }
/* column grid */
.grid { display: inline-grid; grid-auto-rows: 10mm; gap: 0; border-collapse: collapse; }
.grid .g { width: 8.4mm; height: 10mm; border: 1px solid #bbb; display: flex; align-items: center; justify-content: center; font-size: 14pt; margin: -0.5px; }
.grid .g.op { border: none; font-size: 14pt; }
.grid .g.carry { height: 5.5mm; border: 1px dashed #999; font-size: 8pt; }
.grid .g.worked { border: 1px dashed #999; }
.grid .g.ans { border: 1px solid #111; border-top: 2px solid #111; background: #fff; }
.grid .g.line { border: none; border-top: 1.5px solid #111; height: 0; }
.grid .g.res { border-top: 2px solid #111; }
.grid .g.blank { border: none; }
table.sort { border-collapse: collapse; font-size: 10.5pt; }
table.sort th, table.sort td { border: 1px solid #333; padding: 1.2mm 3mm; text-align: center; }
table.sort td:first-child { text-align: left; font-family: "DejaVu Sans Mono", monospace; }
table.square { border-collapse: collapse; font-size: 12pt; }
table.square th, table.square td { border: 1px solid #333; min-width: 11mm; height: 9mm; padding: 0 1mm; text-align: center; }
table.square th { background: #eee; }
.method .step { margin-bottom: 2.5mm; }
.expanded { display: inline-grid; grid-template-columns: max-content calc(var(--w) * 8.4mm + 2mm); column-gap: 3mm; row-gap: 1.5mm; align-items: center; }
.expanded .lab { white-space: nowrap; font-size: 11pt; }
.expanded .xn { display: flex; justify-content: flex-end; }
.expanded .xn.sum { border-top: 1px solid #111; padding-top: 1.5mm; }
.expanded .xd { display: inline-block; width: 8.4mm; text-align: center; font-size: 13pt; }
.expanded .xop { font-size: 13pt; text-align: right; }
table.gridm, table.lattice { border-collapse: collapse; font-size: 12pt; margin-bottom: 3mm; }
table.gridm th, table.gridm td { border: 1px solid #333; padding: 1.5mm 2mm; text-align: center; }
table.gridm th { background: #eee; min-width: 11mm; }
table.lattice th { min-width: 22mm; height: 8mm; text-align: center; }
table.lattice td.lat { position: relative; width: 22mm; height: 22mm; border: 1px solid #333; padding: 0;
  background: linear-gradient(to bottom right, transparent calc(50% - 0.6px), #333 calc(50% - 0.6px), #333 calc(50% + 0.6px), transparent calc(50% + 0.6px)); }
table.lattice td.lat .cells { position: absolute; inset: 0; }
table.lattice td.lat .cell:nth-child(1) { position: absolute; left: 1.8mm; top: 1.8mm; }
table.lattice td.lat .cell:nth-child(2) { position: absolute; right: 1.8mm; bottom: 1.8mm; }
.wall { display: flex; flex-direction: column; align-items: center; gap: 0; }
.wall .r { display: flex; }
.wall .b { width: var(--brick, 24mm); height: 11mm; border: 1px solid #111; display: flex; align-items: center; justify-content: center; font-size: 12pt; margin: -0.5px; }
.cards { display: inline-flex; gap: 3mm; margin: 1.5mm 0; }
.card { width: 10mm; height: 13mm; border: 1.5px solid #111; border-radius: 1mm; display: flex; align-items: center; justify-content: center; font-size: 15pt; font-weight: bold; background: #f4f4f4; }
svg text { font-family: "DejaVu Sans", Arial, sans-serif; }
"""


# What this page's CSS draws, rule by rule, for a layout row to be compared against (`overrides`).
DRAWN = dict(
    re.findall(
        r"(?:^|\} )(\.work(?:\.h\d)?|\.rowgroup \.item \.work) \{[^}]*?min-height: (\d+)mm;", CSS, re.M
    )
)


def overrides(layout):
    """The CSS a layout row (`render.layouts`, goals/s18-read-as-printed.yaml) draws differently from this page's
    own: nothing for today's row, the working space's old heights for a paper printed before L3."""
    if not layout:
        return ""
    wanted = {".work": layout["work_mm"][0], ".rowgroup .item .work": layout["paired_work_mm"]}
    wanted |= {f".work.h{k}": mm for k, mm in zip((2, 3, 4), layout["work_mm"][1:])}
    return " ".join(f"{sel} {{ min-height: {mm}mm; }}" for sel, mm in wanted.items() if int(DRAWN[sel]) != mm)
