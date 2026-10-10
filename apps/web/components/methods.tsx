// Division's written layouts as the child meets them on the page (engine/assess/divide_pages.py and answer_space.py
// `divided`, goals/md3d-division-methods.yaml): the division layout with a small blank before each digit where an
// exchange is written, chunking's take-aways, and long division's rows — a blank for every step, never a code.
import type { ItemRow } from "@/lib/queries-bank";

// The steps a written division prints, in order: every box but the answer, its remainder and an exchange.
const steps = (it: ItemRow) => it.responses.filter((r) => r.rid !== "ans" && r.rid !== "rem" && !r.rid.startsWith("x"));
const leaves = (it: ItemRow) => it.responses.some((r) => r.rid === "rem");

// The division layout as the school writes it (D01, 84 ÷ 4): the quotient's line above the number divided, the divisor
// and its bracket, "r" beside the quotient where there is a remainder, and a small blank before every digit but the
// first, where a remainder exchanged into it is written (engine/assess/answer_space.py `divided`).
export function DivisionLayout({ a, b, rem }: { a: number | string; b: number | string; rem: boolean }) {
  return (
    <span
      role="img"
      aria-label={`${a} ÷ ${b} in the division layout`}
      className="fact inline-grid grid-cols-[auto_auto] leading-[1.45]"
    >
      <span />
      <span>___{rem ? " r ___" : null}</span>
      <span className="border-r border-basalt/60 pr-[4px]">{b}</span>
      <span className="border-t border-basalt/60 pl-[4px]">
        {String(a)
          .split("")
          .map((d, i) => (
            <span key={i}>
              {i > 0 ? <span className="mx-px align-super text-[0.6em] text-basalt/60">▫</span> : null}
              {d}
            </span>
          ))}
      </span>
    </span>
  );
}

// Chunking (96 ÷ 4): for each place, what is taken away and its lots, then what is left; then the lots added.
export function Chunking({ it }: { it: ItemRow }) {
  const { a, b } = it.spec;
  const takes = Math.floor(steps(it).length / 3);
  return (
    <span role="img" aria-label={`${a} ÷ ${b} by chunking`} className="fact inline-grid gap-[2px] leading-[1.45]">
      <span className="pl-[1.2em]">{a}</span>
      {Array.from({ length: takes }, (_, i) => (
        <span key={i} className="grid">
          <span>
            − ___ (___ × {b})
          </span>
          <span className="w-fit border-t border-basalt/60 pl-[1.2em]">___ left</span>
        </span>
      ))}
      <span>
        {a} ÷ {b} = ___{leaves(it) ? " r ___" : null}
      </span>
    </span>
  );
}

// Long division (516 ÷ 4): the quotient's blank over the number divided, the divisor and its bracket, then a row for
// each product, ruled under, and each number left with its digit brought down.
export function LongDivision({ it }: { it: ItemRow }) {
  const { a, b } = it.spec;
  return (
    <span role="img" aria-label={`${a} ÷ ${b} in long division`} className="fact inline-grid gap-[2px] leading-[1.45]">
      <span className="pl-[2em]">___{leaves(it) ? " r ___" : null}</span>
      <span>
        <span className="border-r border-basalt/60 pr-[4px]">{b}</span>
        <span className="border-t border-basalt/60 pl-[4px]">{a}</span>
      </span>
      {steps(it).map((r, i) => (
        <span key={r.rid} className={`w-fit pl-[2em] ${i % 2 === 0 ? "border-b border-basalt/60" : ""}`}>
          {i % 2 === 0 ? "− " : ""}___
        </span>
      ))}
    </span>
  );
}
