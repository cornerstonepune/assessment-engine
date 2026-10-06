"""The questions a child answers from a drawing, drawn: a balance, a number line's jumps, a tally, equal groups. Pure.

`render.render_item` hands each of these kinds here with a way to draw an answer's boxes, so every picture on a page
is drawn in one place and a new one is an entry in `DRAW`, not another branch in the page's renderer
(goals/g1-taught-till-september.yaml).
"""

import html
from collections.abc import Callable
from typing import Any

from engine.assess.answer_space import op_sign
from engine.assess.items import Response

Boxes = Callable[[Response, bool], str]  # an answer's boxes; True draws them big, as Grade 1's are
PX = 0.35  # mm a drawing's unit prints at

STROKE, BUNDLE, LINE = 7, 41, 28  # a tally: units between lines, a bundle and its gap, a line's height
# where a die puts 1 to 6 dots, in steps from the middle of its ring: a group of four reads as four at a glance
DIE = {
    1: [(0, 0)],
    2: [(-1, -1), (1, 1)],
    3: [(-1, -1), (0, 0), (1, 1)],
    4: [(-1, -1), (1, -1), (-1, 1), (1, 1)],
    5: [(-1, -1), (1, -1), (0, 0), (-1, 1), (1, 1)],
    6: [(-1, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (1, 1)],
}


def _svg(width: int, height: int, inside: str, attrs: str = "") -> str:
    return (
        f'<svg width="{width * PX:.1f}mm" height="{height * PX:.1f}mm" viewBox="0 0 {width} {height}"{attrs}>'
        f"{inside}</svg>"
    )


def tally_marks(n: int) -> str:
    """`n` as tally marks: bundles of four upright lines crossed by a fifth, then the lines left over."""
    bundles, ones = divmod(n, 5)
    lines: list[str] = []
    for b in range(bundles):
        x = 6 + b * BUNDLE
        lines += [f'<line x1="{x + i * STROKE}" y1="4" x2="{x + i * STROKE}" y2="{LINE}"/>' for i in range(4)]
        lines.append(f'<line x1="{x - 4}" y1="{LINE - 4}" x2="{x + 3 * STROKE + 4}" y2="8"/>')
    x = 6 + bundles * BUNDLE
    lines += [f'<line x1="{x + i * STROKE}" y1="4" x2="{x + i * STROKE}" y2="{LINE}"/>' for i in range(ones)]
    return _svg(
        x + ones * STROKE + 6, LINE + 4, "".join(lines), ' class="tally" stroke="#111" stroke-width="2"'
    )


def rings(groups: int, size: int) -> str:
    """`groups` rings, each holding `size` dots laid out as a die shows them."""
    parts: list[str] = []
    for g in range(groups):
        cx = 22 + g * 46
        parts.append(
            f'<circle class="group" cx="{cx}" cy="22" r="19" fill="none" stroke="#111" stroke-width="1.5"/>'
        )
        parts += [
            f'<circle class="dot" cx="{cx + dx * 9}" cy="{22 + dy * 9}" r="3.2"/>' for dx, dy in DIE[size]
        ]
    return _svg(groups * 46, 44, "".join(parts), ' fill="#111"')


def tally(sp: dict[str, Any], R: dict[str, Response], box: Boxes, big: bool) -> str:
    if sp["shape"] == "READ":
        drawn = f'<div class="row">{tally_marks(sp["count"])}</div>'
    else:
        rows = "".join(
            f"<tr><td>{html.escape(t)}</td><td>{tally_marks(n)}</td></tr>"
            for t, n in zip(sp["things"], (sp["a"], sp["b"]), strict=True)
        )
        drawn = f'<table class="sort">{rows}</table>'
    return drawn + f'<div class="row"><span class="lab">Answer</span>{box(R["ans"], big)}</div>'


def equal_groups(sp: dict[str, Any], R: dict[str, Response], box: Boxes, big: bool) -> str:
    drawn = {
        "SUM": f'<span class="eq">{" + ".join([str(sp["b"])] * sp["a"])} =</span>',
        "PICTURE": rings(sp["a"], sp["b"]),
    }.get(sp["shape"], '<span class="lab">Answer</span>')  # a story is its own sentence
    return f'<div class="row">{drawn}{box(R["ans"], big)}</div>'


def balance_scale(sp: dict[str, Any], R: dict[str, Response], box: Boxes, big: bool) -> str:
    L, Rr = sp["left"], sp["right"]
    return f"""<svg width="120mm" height="26mm" viewBox="0 0 240 52"><rect x="8" y="6" width="34" height="18" fill="none" stroke="#111"/><text x="25" y="19" text-anchor="middle" font-size="11">{L[0]}</text>
<rect x="42" y="6" width="34" height="18" fill="none" stroke="#111"/><text x="59" y="19" text-anchor="middle" font-size="11">{L[1]}</text>
<rect x="164" y="6" width="34" height="18" fill="none" stroke="#111" stroke-dasharray="3 2"/><text x="181" y="19" text-anchor="middle" font-size="14">?</text>
<rect x="198" y="6" width="34" height="18" fill="none" stroke="#111"/><text x="215" y="19" text-anchor="middle" font-size="11">{Rr[1]}</text>
<line x1="4" y1="26" x2="236" y2="26" stroke="#111" stroke-width="2"/><polygon points="120,26 108,46 132,46" fill="#999"/></svg>
<div class="row"><span class="lab">? =</span>{box(R["ans"], False)}</div>"""


def number_line_jumps(sp: dict[str, Any], R: dict[str, Response], box: Boxes, big: bool) -> str:
    a, op, tens, ones = sp["a"], sp["op"], sp["tens"], sp["ones"]
    d = 1 if op == "+" else -1
    return f'''<div class="row"><span class="eq">{a} {op_sign(op)} {sp["b"]} =</span>{box(R["ans"], False)}</div>
<svg width="150mm" height="24mm" viewBox="0 0 300 48"><line x1="10" y1="34" x2="290" y2="34" stroke="#111" stroke-width="1.5"/><polygon points="290,34 283,30 283,38" fill="#111"/>
<path d="M{40 if d > 0 else 260} 34 Q {(40 + 150) / 2 if d > 0 else (260 + 150) / 2} 2 150 34" fill="none" stroke="#111" stroke-width="1.2"/><text x="{95 if d > 0 else 205}" y="12" text-anchor="middle" font-size="10">{op_sign(op)}{tens}</text>
<path d="M150 34 Q {(150 + 215) / 2 if d > 0 else (150 + 85) / 2} 12 {215 if d > 0 else 85} 34" fill="none" stroke="#111" stroke-width="1.2"/><text x="{182 if d > 0 else 118}" y="20" text-anchor="middle" font-size="10">{op_sign(op)}{ones}</text>
<line x1="{40 if d > 0 else 260}" y1="30" x2="{40 if d > 0 else 260}" y2="38" stroke="#111"/><text x="{40 if d > 0 else 260}" y="47" text-anchor="middle" font-size="10">{a}</text>
<line x1="150" y1="30" x2="150" y2="38" stroke="#111"/><line x1="{215 if d > 0 else 85}" y1="30" x2="{215 if d > 0 else 85}" y2="38" stroke="#111"/></svg>
<div class="row" style="margin-left:{"58mm" if d > 0 else "30mm"}"><span class="lab">lands on</span>{box(R["land1"], False)}</div>'''


DRAW: dict[str, Callable[[dict[str, Any], dict[str, Response], Boxes, bool], str]] = {
    "balance_scale": balance_scale,
    "number_line_jumps": number_line_jumps,
    "tally": tally,
    "equal_groups": equal_groups,
}
