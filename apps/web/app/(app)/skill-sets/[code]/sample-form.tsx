"use client";

import { useActionState } from "react";
import Link from "@/components/link";
import type { SampleChoices } from "@/lib/queries-skills";
import { addKind, saveSample, type SampleState } from "./sample-actions";
import { BLANK, NEW_PASSAGE, type SampleInitial } from "./sample-shape";

// The form an educator changes one English sample in, or the three a new kind needs (goals/edt_edit_samples_and_kinds.yaml).
// It holds what the child sees: the passage, what the child is told, the sentence, the options, gaps or pairs, the right
// answer, and each likely wrong answer with the mistake it shows. Every list is one line per item. The engine checks it
// when it is saved; what fails comes back in words beside its field, and what was typed stays.

const SPARE_WRONG = 2; // empty rows for more likely wrong answers

const OPTIONS = new Set(["ENG.CHOOSE", "ENG.GAP", "ENG.ORDER", "ENG.SORT"]);
const ANSWER_SAYS: Record<string, string> = {
  "ENG.ORDER": "The items in the right order, one per line.",
  "ENG.MARK_WORDS": "The words to mark, one per line.",
  "ENG.MATCH": "One line per pair: left - right.",
  "ENG.SORT": "One line per item: item: group.",
  "ENG.TABLE": "One line per box: box: what goes in it.",
  "ENG.GAP": "The word that goes in the gap.",
  "ENG.CHOOSE": "The right option, exactly as printed.",
};
const WRONG_SAYS: Record<string, string> = {
  "ENG.CHOOSE": "a printed option",
  "ENG.ORDER": "every item once, in another order, with commas: a, b, c",
  "ENG.MATCH": "a pair the key does not make: left - right",
  "ENG.SORT": "an item in the wrong group: item: group",
  "ENG.TABLE": "a box with the wrong words: box: words",
  "ENG.MARK_WORDS": "words of the text, with commas between them",
  "ENG.COPY": "words of the passage",
  "ENG.PUNCTUATE": "the same words, punctuated wrongly",
};

function Faults({ f }: { f?: string[] }) {
  if (!f?.length) return null;
  return (
    <ul className="grid gap-[2px] text-[13px] font-semibold text-terracotta" role="alert">
      {f.map((x) => (
        <li key={x}>{x}</li>
      ))}
    </ul>
  );
}

type FieldsProps = {
  p: string;
  kind: string;
  open: boolean;
  start: SampleInitial;
  choices: SampleChoices;
  faults?: Record<string, string[]>;
  sent?: Record<string, string[]>;
};

/** One sample's fields, their names under `p` (a kind's three samples are "s0.", "s1.", "s2."). */
function SampleFields({ p, kind, open, start, choices, faults = {}, sent }: FieldsProps) {
  const was = (name: string, fallback: string | null | undefined) => sent?.[p + name]?.[0] ?? fallback ?? "";
  const field = (name: string) => was(name, start.fields[name]);
  const wrongAnswers = sent?.[`${p}wrong_answer`] ?? start.wrong.map((w) => w.answer);
  const wrongMistakes = sent?.[`${p}wrong_mistake`] ?? start.wrong.map((w) => w.mistake_code);
  const rows = Math.max(wrongAnswers.length, start.wrong.length) + (sent ? 0 : SPARE_WRONG);
  const area = (name: string, label: string, note?: string, rowsN = 3) => (
    <label className="field">
      <span className="label">{label}</span>
      <textarea className="textarea" name={p + name} defaultValue={field(name)} rows={rowsN} aria-invalid={Boolean(faults[name])} />
      {note ? <span className="note">{note}</span> : null}
      <Faults f={faults[name]} />
    </label>
  );
  return (
    <div className="grid gap-3">
      <label className="field">
        <span className="label">Passage</span>
        <select className="select" name={`${p}passage`} defaultValue={was("passage", start.passage_code)}>
          <option value="">No passage</option>
          {choices.passages.map((x) => (
            <option key={x.code} value={x.code}>
              {x.title}
            </option>
          ))}
          <option value={NEW_PASSAGE}>Write a new passage (below)</option>
        </select>
        <Faults f={faults.passage} />
      </label>
      <details className="text-[13px]" open={was("passage", start.passage_code) === NEW_PASSAGE}>
        <summary className="cursor-pointer">A new passage</summary>
        <div className="mt-2 grid gap-2">
          <label className="field">
            <span className="label">Its title</span>
            <input className="input" name={`${p}passage_title`} defaultValue={was("passage_title", "")} />
          </label>
          <label className="field">
            <span className="label">Its text</span>
            <textarea className="textarea" name={`${p}passage_text`} defaultValue={was("passage_text", "")} rows={6} />
          </label>
        </div>
      </details>
      <label className="field">
        <span className="label">What the child is told</span>
        <input className="input" name={`${p}ask`} defaultValue={field("ask")} aria-invalid={Boolean(faults.ask)} />
        <Faults f={faults.ask} />
      </label>
      {area("text", "The sentence or words printed under it", "Write a gap as ___ (three underscores).", 2)}
      {kind === "ENG.MATCH" ? (
        <div className="grid gap-2">
          <div className="grid gap-3 md:grid-cols-2">
            {area("left", "Left column, one per line")}
            {area("right", "Right column, one per line")}
          </div>
          <Faults f={faults.options} />
        </div>
      ) : OPTIONS.has(kind) || field("options") ? (
        area("options", kind === "ENG.GAP" ? "The box of words, one per line (may be empty)" : "Options, one per line")
      ) : null}
      {area("answer", open ? "An example of a right answer" : "The right answer", ANSWER_SAYS[kind], 2)}
      {area("accept", "Other answers taken as right, one per line (may be empty)", undefined, 2)}
      {open ? (
        <>
          <label className="field">
            <span className="label">What a person reads the answer against</span>
            <select className="select" name={`${p}rubric`} defaultValue={was("rubric", start.rubric_code)}>
              <option value="">Choose</option>
              {choices.rubrics.map((r) => (
                <option key={r.code} value={r.code}>
                  {r.name}
                </option>
              ))}
            </select>
            <Faults f={faults.rubric} />
          </label>
          {area("key_points", "What a right answer does, one per line")}
        </>
      ) : null}
      <fieldset className="grid gap-2" aria-label="Likely wrong answers">
        <legend className="label">Likely wrong answers, and the mistake each shows</legend>
        {WRONG_SAYS[kind] ? <span className="note">Each is {WRONG_SAYS[kind]}.</span> : null}
        <Faults f={faults.wrong} />
        {Array.from({ length: rows }, (_, i) => (
          <div key={i} data-wrong={i} className="grid gap-1">
            <div className="grid gap-2 md:grid-cols-[1fr_1fr]">
              <input
                className="input"
                name={`${p}wrong_answer`}
                aria-label={`Wrong answer ${i + 1}`}
                defaultValue={wrongAnswers[i] ?? ""}
                aria-invalid={Boolean(faults[`wrong.${i}`])}
              />
              <select className="select" name={`${p}wrong_mistake`} aria-label={`Mistake ${i + 1}`} defaultValue={wrongMistakes[i] ?? ""}>
                <option value="">The mistake it shows</option>
                {choices.mistakes.map((m) => (
                  <option key={m.code} value={m.code}>
                    {m.name}
                  </option>
                ))}
              </select>
            </div>
            <Faults f={faults[`wrong.${i}`]} />
          </div>
        ))}
      </fieldset>
      <details className="text-[13px]">
        <summary className="cursor-pointer">Words shown on purpose that are not words</summary>
        <div className="mt-2">{area("not_words", "One per line: a misspelling to fix, a word part such as -ing")}</div>
      </details>
    </div>
  );
}

type Where = { code: string; level: string; kind: string; kindWords: string; open: boolean; choices: SampleChoices };

const WORDS = ["none", "one", "two", "three", "four", "five", "six"];
const said = (n: number) => WORDS[n] ?? String(n);

const EMPTY: SampleState = { faults: {} };

function Refused({ state }: { state: SampleState }) {
  const n = Object.keys(state.faults).length + (state.samples ?? []).reduce((a, f) => a + Object.keys(f ?? {}).length, 0);
  if (!n && !state.why) return null;
  return (
    <div className="grid gap-1 border-l-4 border-terracotta bg-chalk p-2 text-[13.5px]" role="alert">
      <span className="font-semibold">Not saved. {state.why ?? `Fix what is marked below (${n}), then save again.`}</span>
      <Faults f={state.faults.skill} />
    </div>
  );
}

/** One sample changed (`ord`) or added (no `ord`). */
export function SampleForm({ code, level, kind, kindWords, open, choices, ord, start }: Where & { ord: number | null; start: SampleInitial }) {
  const [state, action, busy] = useActionState(saveSample, EMPTY);
  return (
    <form action={action} className="grid gap-3 border-2 border-terracotta/40 bg-chalk p-3" aria-label={ord ? `Change sample ${ord}` : "Add a sample"}>
      <h6 className="text-[14px] font-semibold">
        {ord ? `Change sample ${ord}` : "Add a sample"} · {kindWords}
      </h6>
      <input type="hidden" name="code" value={code} />
      <input type="hidden" name="level" value={level} />
      <input type="hidden" name="kind" value={kind} />
      {ord ? <input type="hidden" name="ord" value={ord} /> : null}
      <Refused state={state} />
      <SampleFields p="" kind={kind} open={open} start={start} choices={choices} faults={state.faults} sent={state.sent} />
      <div className="flex flex-wrap items-center gap-3">
        <button className="btn" type="submit" disabled={busy}>
          Save this sample
        </button>
        <Link href={`/skill-sets/${code}#level-${level}`} className="chip">
          Cancel
        </Link>
        <span className="note">Saving sends {level} back for approval; the sample it replaces is kept.</span>
      </div>
    </form>
  );
}

/** A kind added to a level with its three samples, saved together or not at all. */
export function KindForm({ code, level, kind, kindWords, open, choices, n }: Where & { n: number }) {
  const [state, action, busy] = useActionState(addKind, EMPTY);
  return (
    <form action={action} className="grid gap-3 border-2 border-terracotta/40 bg-chalk p-3" aria-label={`Add ${kindWords}`}>
      <h6 className="text-[14px] font-semibold">
        Add &ldquo;{kindWords}&rdquo; to {level}
      </h6>
      <p className="note">
        {n
          ? `Add ${said(n)} ${n === 1 ? "sample" : "samples"} for this kind: a level shows ${said(choices.few)} of each.`
          : `This level has ${said(choices.few)} samples of this kind already.`}
      </p>
      <input type="hidden" name="code" value={code} />
      <input type="hidden" name="level" value={level} />
      <input type="hidden" name="kind" value={kind} />
      <input type="hidden" name="samples" value={n} />
      <Refused state={state} />
      {Array.from({ length: n }, (_, i) => (
        <fieldset key={i} className="grid gap-2 border border-basalt/12 p-2" aria-label={`Sample ${i + 1}`}>
          <legend className="label">Sample {i + 1}</legend>
          <SampleFields p={`s${i}.`} kind={kind} open={open} start={BLANK} choices={choices} faults={state.samples?.[i]} sent={state.sent} />
        </fieldset>
      ))}
      <div className="flex flex-wrap items-center gap-3">
        <button className="btn" type="submit" disabled={busy}>
          Add this kind
        </button>
        <Link href={`/skill-sets/${code}#level-${level}`} className="chip">
          Cancel
        </Link>
        <span className="note">Adding a kind sends {level} back for approval.</span>
      </div>
    </form>
  );
}
