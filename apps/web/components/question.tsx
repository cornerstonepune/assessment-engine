import { Fragment } from "react";
import Link from "@/components/link";
import { Drawn, Grid, Lattice, Stem } from "@/components/pictures";
import type { ItemResponse, ItemRow, Mistake } from "@/lib/queries-bank";

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
  missing_digit: "missing digit",
  equation: "make both sides equal",
  fact_family: "fact family",
  inverse_check: "check with the inverse",
  choose_estimate: "closest estimate",
  possible_answer: "could it be right?",
  odd_even: "odd or even",
  break_apart: "tens, then ones",
  tally: "tally marks",
  equal_groups: "equal groups",
  skip_counting: "skip counting",
  multiplication_square: "multiplication square",
  repeated_subtraction: "repeated subtraction",
  partitioning: "partitioning",
  grid_method: "grid method",
  expanded_columns: "expanded columns",
  lattice: "lattice",
};

// The kinds of question on the school's own papers, read before our printed sheets; the bank's are `KIND`'s.
const EARLIER: Record<string, string> = {
  legacy_bare: "sum (earlier paper)",
  legacy_missing: "missing number (earlier paper)",
  legacy_word: "word problem (earlier paper)",
  legacy_text: "written answer (earlier paper)",
};
/** A kind of question (`item.fmt`) in the school's words: the bank's, an earlier paper's, or its own name spelt out. */
export const kindWords = (fmt: string) => KIND[fmt] ?? EARLIER[fmt] ?? fmt.replace(/_/g, " ");

// Kinds that print their own sentence. The other three draw their printed line from their numbers
// alone, so there is no wording to correct — the engine refuses it (`engine/question.py`); this only
// decides whether the page offers it.
export const printsItsWording = (fmt: string) => !["bare_sum", "column_grid", "missing_number"].includes(fmt);

const SIGN: Record<string, string> = { "-": "−", "*": "×" };
const sign = (op?: string) => (op ? (SIGN[op] ?? op) : "");

// A number by its places, its zero places left out (23 → 20, 3), as a written method partitions it
// (engine/assess/written_methods.py).
const parts = (n: number) =>
  String(n)
    .split("")
    .map((d, i, all) => Number(d) * 10 ** (all.length - 1 - i))
    .filter((p) => p > 0);

// A written method's steps, each as the paper prints it with a blank to fill, then the total.
function Steps({ it, plain }: { it: ItemRow; plain?: boolean }) {
  return (
    <span className="grid gap-[3px]">
      {it.responses
        .filter((r) => r.rid !== "ans")
        .map((r) => (
          <span key={r.rid} className="fact">
            {plain ? (r.label ?? "").replace(/ =$/, "") : r.label} ___
          </span>
        ))}
    </span>
  );
}

/** The question as the child meets it on the page — the sum, the sentence, the wall — never a code. */
export function Question({ it }: { it: ItemRow }) {
  const s = it.spec;
  switch (it.fmt) {
    case "column_grid":
      return s.op === "÷" ? (
        <Divided a={s.a ?? 0} b={s.b ?? 0} rem={leaves(it)} />
      ) : (
        <Column numbers={s.addends ?? [s.a ?? 0, s.b ?? 0]} op={sign(s.op)} />
      );
    case "bare_sum":
      // asked in words, the sentence alone ("How many 6s make 42?"): the sign would give it away
      if (s.text) return <span>{s.text}</span>;
      return (
        <span className="fact">
          {s.addends ? s.addends.join(` ${sign(s.op)} `) : `${s.a} ${sign(s.op)} ${s.b}`} = ___
          {leaves(it) ? " r ___" : null}
        </span>
      );
    case "missing_digit":
      // a division is its sentence (7□ ÷ 4 = 18), never a column
      return s.shape || s.op === "÷" ? (
        <span>{it.stem}</span>
      ) : (
        <Column numbers={[s.a ?? "", s.b ?? ""]} op={sign(s.op)} result={s.c} />
      );
    case "equation":
      return (
        <Stem text={it.stem}>
          <span className="fact">{s.text}</span>
        </Stem>
      );
    case "fact_family":
    case "inverse_check":
      // the table backwards is its two sentences (42 ÷ 6 = □, 6 × □ = 42); a check of a claimed answer says its sum
      if (!s.facts) return <span>{it.stem}</span>;
      return (
        <Stem text={it.stem}>
          <span className="fact grid gap-[2px]">
            {(s.facts ?? []).map((f: string) => (
              <span key={f}>{f}</span>
            ))}
          </span>
        </Stem>
      );
    case "choose_estimate":
      return (
        <Stem text={it.stem}>
          <span className="fact">{(s.options ?? []).join(" · ")}</span>
        </Stem>
      );
    case "missing_number":
      return <span className="fact">{s.text ?? it.stem}</span>;
    case "number_wall":
      return (
        <Stem text={it.stem}>
          <Wall base={s.base ?? []} />
        </Stem>
      );
    case "tally":
    case "equal_groups":
    case "skip_counting":
    case "multiplication_square":
    case "repeated_subtraction":
      return <Drawn it={it} />;
    case "partitioning":
      return (
        <Stem text={it.stem}>
          <Steps it={it} />
          <span className="fact">{s.a} × {s.b} = ___</span>
        </Stem>
      );
    case "expanded_columns":
      return (
        <Stem text={it.stem}>
          <Column numbers={[s.a ?? 0, s.b ?? 0]} op="×" />
          <Steps it={it} plain />
          <span className="fact">total ___</span>
        </Stem>
      );
    case "grid_method": {
      const [a, b] = [Number(s.a), Number(s.b)];
      const onTop = parts(a).length >= parts(b).length;
      return (
        <Stem text={it.stem}>
          <Grid a={a} b={b} top={onTop ? parts(a) : parts(b)} side={onTop ? parts(b) : parts(a)} />
          <span className="fact">{a} × {b} = ___</span>
        </Stem>
      );
    }
    case "lattice":
      return (
        <Stem text={it.stem}>
          <Lattice a={Number(s.a)} b={Number(s.b)} />
          <span className="fact">{s.a} × {s.b} = ___</span>
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
      // A story that says "the table shows…" carries its numbers in the table, not the sentence.
      return s.table ? (
        <Stem text={it.stem}>
          <span className="fact grid w-fit grid-cols-[auto_auto] gap-x-4">
            {s.table.map(([label, n]) => (
              <Fragment key={label}>
                <span>{label}</span>
                <span className="text-right">{n}</span>
              </Fragment>
            ))}
          </span>
        </Stem>
      ) : (
        <span>{it.stem || s.question || s.text}</span>
      );
  }
}

const box = (n: number | null) => (n === null ? "□" : String(n));

// A division that leaves a remainder asks for it in a box of its own, after "r" (ADR 0056).
const leaves = (it: ItemRow) => it.responses.some((r) => r.rid === "rem");

// Numbers stacked on their place-value columns, the sign beside the last, a line to write under.
function Column({ numbers, op, result }: { numbers: (number | string)[]; op: string; result?: string }) {
  return (
    <span className="fact inline-grid justify-items-end leading-[1.45]">
      {numbers.map((n, i) => (
        <span key={i}>{i === numbers.length - 1 ? `${op} ${n}` : n}</span>
      ))}
      <span className="h-[1.3em] w-full border-t border-basalt/60">{result ?? null}</span>
    </span>
  );
}

// The division layout as the school writes it (D01, 84 ÷ 4): the quotient's line above the number divided, the divisor
// and its bracket, "r" beside the quotient where there is a remainder (engine/assess/answer_space.py `divided`).
function Divided({ a, b, rem }: { a: number | string; b: number | string; rem: boolean }) {
  return (
    <span
      role="img"
      aria-label={`${a} ÷ ${b} in the division layout`}
      className="fact inline-grid grid-cols-[auto_auto] leading-[1.45]"
    >
      <span />
      <span>___{rem ? " r ___" : null}</span>
      <span className="border-r border-basalt/60 pr-[4px]">{b}</span>
      <span className="border-t border-basalt/60 pl-[4px]">{a}</span>
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

// What a person reads an explanation against. A worked answer's "why" is read against its planted mistake's own row,
// named beside it (`Mistakes`): never the name a question stored before M3b3, a copy the code kept, which could say
// otherwise than the row the school edits (goals/md3b3-divide-mistakes-and-stories.yaml).
const looksFor = (it: ItemRow, r: ItemResponse) => (it.spec.planted ? "Names the mistake its worked answer shows" : r.rubric);

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
            <span className="note" title={looksFor(it, r) ?? undefined}>
              in words · a teacher reads it
              {rubric && looksFor(it, r) ? <span className="block text-basalt/70">Looks for: {looksFor(it, r)}</span> : null}
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
