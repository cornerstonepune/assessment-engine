import type { ReactNode } from "react";
import Link from "@/components/link";
import type { ItemRow, Mistake } from "@/lib/queries-bank";

// The kinds of question the bank holds, in the words a teacher uses, keyed by `item.fmt`. A label
// lives beside the renderer that draws its question: a new kind needs both, so they arrive together.
export const KIND: Record<string, string> = {
  column_grid: "column sum",
  bare_sum: "horizontal sum",
  missing_number: "missing number",
  word_1step: "one-step word problem",
  word_2step: "two-step word problem",
  estimate_then_calc: "estimate, then work out",
  efficient_method: "quickest method",
  explain_claim: "true or not? explain",
  find_mistake: "find the mistake",
  number_wall: "number wall",
  balance_scale: "balance the scales",
  number_line_jumps: "number line",
};

// Kinds that print their own sentence. The other three draw their printed line from their numbers
// alone, so there is no wording to correct — the engine refuses it (`engine/question.py`); this only
// decides whether the page offers it.
export const printsItsWording = (fmt: string) => !["bare_sum", "column_grid", "missing_number"].includes(fmt);

const SIGN: Record<string, string> = { "-": "−", "*": "×" };
const sign = (op?: string) => (op ? (SIGN[op] ?? op) : "");

/** The question as the child meets it on the page — the sum, the sentence, the wall — never a code. */
export function Question({ it }: { it: ItemRow }) {
  const s = it.spec;
  switch (it.fmt) {
    case "column_grid":
      return <Column numbers={s.addends ?? [s.a ?? 0, s.b ?? 0]} op={sign(s.op)} />;
    case "bare_sum":
      return (
        <span className="fact">
          {s.a} {sign(s.op)} {s.b} = ___
        </span>
      );
    case "missing_number":
      return <span className="fact">{s.text ?? it.stem}</span>;
    case "number_wall":
      return (
        <Stem text={it.stem}>
          <Wall base={s.base ?? []} />
        </Stem>
      );
    case "balance_scale":
      return (
        <Stem text={it.stem}>
          <span className="fact">
            {(s.left ?? []).map(box).join(" + ")} = {(s.right ?? []).map(box).join(" + ")}
          </span>
        </Stem>
      );
    default:
      return <span>{it.stem || s.question || s.text}</span>;
  }
}

const box = (n: number | null) => (n === null ? "□" : String(n));

function Stem({ text, children }: { text: string; children: ReactNode }) {
  return (
    <span className="grid gap-[6px]">
      <span>{text}</span>
      {children}
    </span>
  );
}

// Numbers stacked on their place-value columns, the sign beside the last, a line to write under.
function Column({ numbers, op }: { numbers: number[]; op: string }) {
  return (
    <span className="fact inline-grid justify-items-end leading-[1.45]">
      {numbers.map((n, i) => (
        <span key={i}>{i === numbers.length - 1 ? `${op} ${n}` : n}</span>
      ))}
      <span className="h-[1.3em] w-full border-t border-basalt/60" />
    </span>
  );
}

// A wall of bricks: the given numbers along the bottom, an empty brick for every sum above.
function Wall({ base }: { base: number[] }) {
  return (
    <span className="grid justify-items-center gap-[3px]">
      {base.map((_, row) => (
        <span key={row} className="flex gap-[3px]">
          {Array.from({ length: row + 1 }, (_, j) => (
            <span key={j} className="fact h-[1.8em] min-w-10 border border-basalt/35 px-1 text-center leading-[1.7em]">
              {row === base.length - 1 ? base[j] : null}
            </span>
          ))}
        </span>
      ))}
    </span>
  );
}

/** Everything the child writes for this question, each part named: an estimate and an exact answer
 *  are two answers, and an explanation is read by a person against its rubric (shown in full with
 *  `rubric`, as a hover otherwise). */
export function Answers({ it, rubric = false }: { it: ItemRow; rubric?: boolean }) {
  return (
    <span className="grid gap-[3px]">
      {it.responses.map((r) => (
        <span key={r.rid}>
          {r.label ? <span className="text-basalt/62">{r.label} </span> : null}
          {r.answer !== null ? (
            <span className="fact">
              {r.answer}
              {r.tolerance ? ` (±${r.tolerance})` : ""}
            </span>
          ) : (
            <span className="note" title={r.rubric ?? undefined}>
              in words · a teacher reads it
              {rubric && r.rubric ? <span className="block text-basalt/70">Looks for: {r.rubric}</span> : null}
            </span>
          )}
        </span>
      ))}
    </span>
  );
}

/** A mistake as this question's own operation names it. Where the question does not record one and
 *  the name depends on it, there is no name to give: another operation's name would be a wrong
 *  statement about the child. `book` is `mistakeBook()`. */
export function mistakeOf(book: Record<string, Mistake>, code: string, op?: string): Mistake | undefined {
  return book[`${code}@${op}`] ?? book[`${code}@any`] ?? book[code];
}

/** The wrong answers this question was built to recognise, each with the named mistake behind it —
 *  and, for find-the-mistake, the mistake its worked example shows. Named mistakes lead; a code with
 *  no name for this question stands in as provenance and goes last. `more` links the rest. */
export function Mistakes({
  it,
  book,
  max = 2,
  more,
}: {
  it: ItemRow;
  book: Record<string, Mistake>;
  max?: number;
  more?: string;
}) {
  const name = (code: string) => mistakeOf(book, code, it.spec.op)?.name;
  const label = (code: string) => name(code) ?? <span className="fact text-[11px]">{code}</span>;
  const caught = it.responses
    .flatMap((r) => Object.entries(r.misconceptions ?? {}))
    .sort(([a], [b]) => Number(!name(a)) - Number(!name(b)));
  const planted = it.spec.planted;
  if (!caught.length && !planted) return <span className="note">—</span>;
  const rest = caught.length - max;
  return (
    <span className="grid gap-[2px] text-[12px] leading-[1.6]">
      {planted ? (
        <span>
          <span className="text-basalt/62">shows · </span>
          {label(planted)}
        </span>
      ) : null}
      {caught.slice(0, max).map(([code, wrong], i) => (
        <span key={`${code}-${i}`}>
          <span className="fact">{wrong}</span>
          <span className="text-basalt/62"> · {label(code)}</span>
        </span>
      ))}
      {rest > 0 ? more ? <Link href={more}>+{rest} more</Link> : <span className="note">+{rest} more</span> : null}
    </span>
  );
}
