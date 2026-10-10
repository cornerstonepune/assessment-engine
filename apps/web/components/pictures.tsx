// The questions a child answers from a drawing, drawn as they print (engine/assess/pictures.py): the website shows
// the child's question, never a code or a description of it.
import { Fragment, type ReactNode } from "react";
import type { ItemRow } from "@/lib/queries-bank";

/** A question's sentence above what it draws. */
export function Stem({ text, children }: { text: string; children: ReactNode }) {
  return (
    <span className="grid gap-[6px]">
      <span>{text}</span>
      {children}
    </span>
  );
}

// A tally: bundles of four lines crossed by a fifth, then the lines left over.
export function Tally({ n }: { n: number }) {
  const bundles = Math.floor(n / 5);
  const ones = n % 5;
  const x = (b: number, i: number) => 6 + b * 41 + i * 7;
  const width = x(bundles, ones) + 6;
  return (
    <svg width={width} height={32} viewBox={`0 0 ${width} 32`} stroke="currentColor" strokeWidth={2} aria-label={`a tally of ${n}`}>
      {Array.from({ length: bundles }, (_, b) => (
        <g key={b}>
          {[0, 1, 2, 3].map((i) => (
            <line key={i} x1={x(b, i)} y1={4} x2={x(b, i)} y2={28} />
          ))}
          <line x1={x(b, 0) - 4} y1={24} x2={x(b, 3) + 4} y2={8} />
        </g>
      ))}
      {Array.from({ length: ones }, (_, i) => (
        <line key={i} x1={x(bundles, i)} y1={4} x2={x(bundles, i)} y2={28} />
      ))}
    </svg>
  );
}

// Where a die puts 1 to 6 dots, in steps from the middle of its ring.
const DIE: Record<number, [number, number][]> = {
  1: [[0, 0]],
  2: [[-1, -1], [1, 1]],
  3: [[-1, -1], [0, 0], [1, 1]],
  4: [[-1, -1], [1, -1], [-1, 1], [1, 1]],
  5: [[-1, -1], [1, -1], [0, 0], [-1, 1], [1, 1]],
  6: [[-1, -1], [1, -1], [-1, 0], [1, 0], [-1, 1], [1, 1]],
};

// Equal groups: a ring per group, its dots laid out as a die shows them.
export function Rings({ groups, size }: { groups: number; size: number }) {
  return (
    <svg width={groups * 46} height={44} viewBox={`0 0 ${groups * 46} 44`} fill="currentColor" aria-label={`${groups} groups of ${size}`}>
      {Array.from({ length: groups }, (_, g) => (
        <g key={g}>
          <circle cx={22 + g * 46} cy={22} r={19} fill="none" stroke="currentColor" strokeWidth={1.5} />
          {(DIE[size] ?? []).map(([dx, dy], i) => (
            <circle key={i} cx={22 + g * 46 + dx * 9} cy={22 + dy * 9} r={3.2} />
          ))}
        </g>
      ))}
    </svg>
  );
}

// An array: rows of dots, evenly spaced, so its rows and the dots in each are read off it.
export function Dots({ rows, each }: { rows: number; each: number }) {
  return (
    <svg width={each * 16 + 4} height={rows * 16 + 4} viewBox={`0 0 ${each * 16 + 4} ${rows * 16 + 4}`} fill="currentColor" aria-label={`${rows} rows of ${each}`}>
      {Array.from({ length: rows }, (_, r) =>
        Array.from({ length: each }, (_, c) => <circle key={`${r}-${c}`} cx={10 + c * 16} cy={10 + r * 16} r={4} />),
      )}
    </svg>
  );
}

// Dots in rows of ten and in no group, for the child to share out into rings or to ring in groups.
export function Loose({ n, label }: { n: number; label: string }) {
  const rows = Math.ceil(n / 10);
  const width = Math.min(n, 10) * 16 + 4;
  return (
    <svg width={width} height={rows * 16 + 4} viewBox={`0 0 ${width} ${rows * 16 + 4}`} fill="currentColor" aria-label={label}>
      {Array.from({ length: n }, (_, i) => (
        <circle key={i} cx={10 + (i % 10) * 16} cy={10 + Math.floor(i / 10) * 16} r={4} />
      ))}
    </svg>
  );
}

// Rings with nothing in them, each wide enough for a share drawn inside.
export function EmptyRings({ n }: { n: number }) {
  return (
    <svg width={n * 60} height={56} viewBox={`0 0 ${n * 60} 56`} aria-label={`${n} empty rings`}>
      {Array.from({ length: n }, (_, g) => (
        <circle key={g} cx={28 + g * 60} cy={28} r={25} fill="none" stroke="currentColor" strokeWidth={1.5} />
      ))}
    </svg>
  );
}

// Equal groups that divide (engine/assess/divide_models.py): dots to share into empty rings, dots to ring in groups, or
// an array read as in all ÷ rows = in each row.
function Divided({ it }: { it: ItemRow }) {
  const a = Number(it.spec.a);
  const b = Number(it.spec.b);
  if (it.spec.method === "ARRAY")
    return (
      <Stem text={it.stem}>
        <Dots rows={b} each={a / b} />
        <span className="fact">in all ___ ÷ rows ___ = in each row ___</span>
      </Stem>
    );
  return it.spec.method === "SHARING" ? (
    <Stem text={it.stem}>
      <Loose n={a} label={`${a} dots to share into ${b} rings`} />
      <EmptyRings n={b} />
    </Stem>
  ) : (
    <Stem text={it.stem}>
      <Loose n={a} label={`${a} dots to ring in groups`} />
    </Stem>
  );
}

// A part of the multiplication square: its rows and columns headed, every cell its row times its column but the one
// asked, left blank.
export function Square({ rows, cols, at }: { rows: number[]; cols: number[]; at: [number, number] }) {
  const cell = "min-w-[2.2em] border border-basalt/40 px-1 text-center";
  return (
    <span className="fact grid w-fit" style={{ gridTemplateColumns: `repeat(${cols.length + 1}, auto)` }} aria-label="part of the multiplication square">
      <span className={`${cell} bg-basalt/10`}>×</span>
      {cols.map((c) => (
        <span key={`c${c}`} className={`${cell} bg-basalt/10`}>{c}</span>
      ))}
      {rows.map((r) => [
        <span key={`r${r}`} className={`${cell} bg-basalt/10`}>{r}</span>,
        ...cols.map((c) => (
          <span key={`${r}-${c}`} className={cell}>{r === at[0] && c === at[1] ? "___" : r * c}</span>
        )),
      ])}
    </span>
  );
}

// A written method's grid (engine/assess/written_pages.py): the parts of the number with more across the top, the
// other's down the side, a blank in every cell.
export function Grid({ a, b, top, side }: { a: number; b: number; top: number[]; side: number[] }) {
  const cell = "min-w-[2.6em] border border-basalt/40 px-1 text-center";
  return (
    <span className="fact grid w-fit" style={{ gridTemplateColumns: `repeat(${top.length + 1}, auto)` }} aria-label={`grid for ${a} × ${b}`}>
      <span className={`${cell} bg-basalt/10`}>×</span>
      {top.map((t) => (
        <span key={`t${t}`} className={`${cell} bg-basalt/10`}>{t}</span>
      ))}
      {side.map((s) => [
        <span key={`s${s}`} className={`${cell} bg-basalt/10`}>{s}</span>,
        ...top.map((t) => (
          <span key={`${s}-${t}`} className={cell}>___</span>
        )),
      ])}
    </span>
  );
}

const DIAGONAL =
  "linear-gradient(to bottom right, transparent calc(50% - 0.5px), currentColor calc(50% - 0.5px), currentColor calc(50% + 0.5px), transparent calc(50% + 0.5px))";

// A lattice: the digits of one number across the top, the other's down the right side, every cell split by its
// diagonal, the tens above it and the ones below.
export function Lattice({ a, b }: { a: number; b: number }) {
  const top = String(a).split("");
  const side = String(b).split("");
  return (
    <span className="fact grid w-fit" style={{ gridTemplateColumns: `repeat(${top.length}, 2.6em) auto` }} aria-label={`lattice for ${a} × ${b}`}>
      {top.map((d, i) => (
        <span key={`t${i}`} className="text-center">{d}</span>
      ))}
      <span />
      {side.map((d, j) => [
        ...top.map((_, i) => <span key={`${j}-${i}`} className="h-[2.6em] border border-basalt/40" style={{ background: DIAGONAL }} />),
        <span key={`s${j}`} className="self-center pl-1">{d}</span>,
      ])}
    </span>
  );
}

/** A question the child answers from a drawing, drawn as the paper draws it (engine/assess/pictures.py `DRAW`). */
export function Drawn({ it }: { it: ItemRow }) {
  const s = it.spec;
  switch (it.fmt) {
    case "tally":
      return (
        <Stem text={it.stem}>
          {s.shape === "READ" ? (
            <Tally n={Number(s.count)} />
          ) : (
            <span className="grid w-fit grid-cols-[auto_auto] items-center gap-x-4">
              {(s.things ?? []).map((thing, i) => (
                <Fragment key={thing}>
                  <span>{thing}</span>
                  <Tally n={Number(i ? s.b : s.a)} />
                </Fragment>
              ))}
            </span>
          )}
        </Stem>
      );
    case "equal_groups":
      if (s.op === "÷") return <Divided it={it} />;
      if (s.shape === "SUM") return <span className="fact">{Array(Number(s.a)).fill(s.b).join(" + ")} = ___</span>;
      if (s.shape === "ARRAY")
        return (
          <Stem text={it.stem}>
            <Dots rows={Number(s.a)} each={Number(s.b)} />
            <span className="fact">rows ___ × in each row ___ = in all ___</span>
          </Stem>
        );
      return s.shape === "PICTURE" ? (
        <Stem text={it.stem}>
          <Rings groups={Number(s.a)} size={Number(s.b)} />
        </Stem>
      ) : (
        <span>{it.stem}</span>
      );
    case "skip_counting":
      return (
        <Stem text={it.stem}>
          <span className="fact">
            {Array.from({ length: Number(s.a) - 1 }, (_, k) => Number(s.b) * (k + 1)).join(", ")}, ___
          </span>
        </Stem>
      );
    case "multiplication_square":
      return (
        <Stem text={it.stem}>
          <Square rows={s.rows ?? []} cols={s.cols ?? []} at={[Number(s.a), Number(s.b)]} />
        </Stem>
      );
    case "repeated_subtraction":
      // the number taken away again and again, printed whole from its numbers: 15 − 3 − 3 − 3 − 3 − 3 = 0
      return (
        <Stem text={it.stem}>
          <span className="fact">
            {[s.a, ...Array(Number(s.a) / Number(s.b)).fill(s.b)].join(" − ")} = 0
          </span>
        </Stem>
      );
    default:
      return <span>{it.stem}</span>;
  }
}
