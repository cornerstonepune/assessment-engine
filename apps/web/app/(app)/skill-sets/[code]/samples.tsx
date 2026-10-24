import Link from "@/components/link";
import { Answers, Question } from "@/components/question";
import type { ItemRow } from "@/lib/queries-bank";
import type { SampleChoices, SampleRow } from "@/lib/queries-skills";
import { dateWords } from "@/lib/week";
import { removeSample } from "./sample-actions";
import { SampleForm } from "./sample-form";
import { BLANK, type SampleInitial } from "./sample-shape";

// A level's sample questions on the skill's page, so an approver reads them before approving the level
// (goals/smp_skill_shows_its_samples.yaml). Nimish, 2026-10-23: "How will the educator approve without having sample
// questions?" Grouped by kind, three of each, each as the child sees it, with the right answer and the likely wrong answers,
// each naming its mistake in words. Drawn by the shared Question and Answers blocks. Whoever may change the skill changes a
// sample here, adds one or removes one (goals/edt_edit_samples_and_kinds.yaml): the form opens in the sample's place.

/** The right answer as Answers writes it: one line, or a line per group, row or pair, named by its group, row or word. */
function answered(a: SampleRow["answer"]): ItemRow["responses"] {
  const line = (rid: string, answer: string, label?: string) => ({ rid, answer, label, misconceptions: {} });
  if (typeof a === "string") return [line("ans", a)];
  if (Array.isArray(a)) {
    return a.every(Array.isArray)
      ? (a as string[][]).map(([l, r]) => line(l, r, `${l} →`))
      : [line("ans", (a as string[]).join(", "))];
  }
  return Object.entries(a).map(([k, v]) => line(k, Array.isArray(v) ? v.join(", ") : v, `${k}:`));
}

/** A sample as the shared blocks read a question. */
const asQuestion = (s: SampleRow): ItemRow => ({
  id: `${s.kind}-${s.ord}`,
  item_key: `${s.kind}-${s.ord}`,
  fmt: s.kind,
  stem: s.ask,
  spec: { printed: { passage: s.passage, text: s.text, options: s.options } },
  responses: answered(s.answer),
  status: "draft",
  times_used: 0,
  skill_set_code: null,
  skill_set_name: null,
  difficulty: s.difficulty,
});

/** Which sample's form is open (`?edit=<level>~<kind>~<number or new>`), the sample as its form shows it, and what the
 *  form picks from; none for someone who may not change the skill. */
export type Editing = {
  code: string;
  open: string | null;
  start: SampleInitial | null;
  choices: SampleChoices;
} | null;

export function LevelSamples({ samples, level, editing }: { samples: SampleRow[]; level: string; editing: Editing }) {
  const here = samples.filter((s) => s.difficulty === level);
  if (!here.length) return <p className="note">No sample questions yet.</p>;
  const kinds = [...new Set(here.map((s) => s.kind))];
  return (
    <div className="grid gap-4" aria-label={`Sample questions at ${level}`}>
      <h4 className="label">Sample questions</h4>
      {kinds.map((k) => {
        const of = here.filter((s) => s.kind === k);
        const rubric = of.find((s) => s.rubric)?.rubric;
        return (
          <section key={k} data-kind={k} aria-label={of[0].kind_words} className="grid gap-2 bg-lime p-3">
            <h5 className="text-[14px] font-semibold">
              {of[0].kind_words}
              {of[0].open ? <span className="font-normal text-basalt/70"> · a person reads every answer</span> : null}
            </h5>
            <ol className="grid gap-3 md:grid-cols-3">
              {of.map((s) => (
                <Sample key={s.ord} s={s} editing={editing} removable={of.length > (editing?.choices.few ?? Infinity)} />
              ))}
            </ol>
            {editing ? <Opened editing={editing} level={level} kind={k} of={of} /> : null}
            {of[0].open && rubric ? (
              <details className="text-[13px]">
                <summary className="cursor-pointer">What a person reads the answer against: {rubric.name}</summary>
                <ul className="mt-2 grid gap-2">
                  {rubric.criteria.map((c) => (
                    <li key={c.code}>
                      <span className="font-semibold">{c.name}</span>
                      <ul className="grid gap-[2px] text-basalt/80">
                        {rubric.scale.map((w) => (
                          <li key={w}>
                            {w}: {c.levels[w]}
                          </li>
                        ))}
                      </ul>
                    </li>
                  ))}
                </ul>
              </details>
            ) : null}
          </section>
        );
      })}
    </div>
  );
}

const slot = (level: string, kind: string, ord: number | "new") => `${level}~${kind}~${ord}`;

/** The form of the sample being changed, or of a new one, under its kind's samples; else the link that adds one. */
function Opened({ editing, level, kind, of }: { editing: NonNullable<Editing>; level: string; kind: string; of: SampleRow[] }) {
  const where = { code: editing.code, level, kind, kindWords: of[0].kind_words, open: of[0].open, choices: editing.choices };
  const ord = of.find((s) => editing.open === slot(level, kind, s.ord))?.ord;
  if (ord && editing.start) return <SampleForm {...where} ord={ord} start={editing.start} />;
  if (editing.open === slot(level, kind, "new")) return <SampleForm {...where} ord={null} start={BLANK} />;
  return (
    <Link href={`/skill-sets/${editing.code}?edit=${slot(level, kind, "new")}#level-${level}`} className="chip justify-self-start">
      Add a sample
    </Link>
  );
}

function Sample({ s, editing, removable }: { s: SampleRow; editing: Editing; removable: boolean }) {
  const here = editing ? slot(s.difficulty, s.kind, s.ord) : "";
  return (
    <li data-sample={s.ord} className={`grid content-start gap-2 border bg-chalk p-2 text-[13.5px] ${editing?.open === here ? "border-terracotta" : "border-basalt/12"}`}>
      <Question it={asQuestion(s)} />
      <div className="grid gap-[2px] border-t border-basalt/12 pt-2" aria-label="The right answer">
        <span className="label text-neem">✓ {s.open ? "A right answer, for example" : "Right answer"}</span>
        <span className="font-semibold">
          <Answers it={asQuestion(s)} />
        </span>
        {s.accept.length ? <span className="text-basalt/70">Also right: {s.accept.join(", ")}</span> : null}
        {s.open && s.key_points?.length ? (
          <span className="text-basalt/70">What a right answer does: {s.key_points.join("; ")}</span>
        ) : null}
      </div>
      {s.wrong.length ? (
        <div className="grid gap-[2px]" aria-label="Likely wrong answers">
          <span className="label">Likely wrong answers</span>
          <ul className="grid gap-[3px]">
            {s.wrong.map((w) => (
              <li key={w.answer}>
                <span className="fact">{w.answer}</span>
                <span className="text-basalt/70"> · {w.mistake}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      {s.edited_by && s.edited_at ? (
        <span className="note">
          Changed by {s.edited_by.split(" (")[0]} · {dateWords(s.edited_at)}
          {s.earlier ? ` · ${s.earlier} earlier ${s.earlier === 1 ? "version" : "versions"} kept` : ""}
        </span>
      ) : null}
      {editing ? (
        <div className="flex flex-wrap items-center gap-2 border-t border-basalt/12 pt-2">
          <Link href={`/skill-sets/${editing.code}?edit=${here}#level-${s.difficulty}`} className="chip" aria-label={`Edit sample ${s.ord}`}>
            Edit
          </Link>
          {removable ? (
            <form action={removeSample}>
              <input type="hidden" name="code" value={editing.code} />
              <input type="hidden" name="level" value={s.difficulty} />
              <input type="hidden" name="kind" value={s.kind} />
              <input type="hidden" name="ord" value={s.ord} />
              <button className="chip" type="submit" aria-label={`Remove sample ${s.ord}`}>
                Remove
              </button>
            </form>
          ) : null}
        </div>
      ) : null}
    </li>
  );
}
