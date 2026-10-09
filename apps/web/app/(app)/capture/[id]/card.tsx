// One answer on the Marking page: the patch of the photograph it was read from, what the engine made of it, the right
// answer as the engine stores it, and what a person is asked — what the child wrote, and, if the stored right answer is
// wrong, what it is for every child (goals/s26-the-right-answer-shown-and-corrected.yaml).
import { mistakeName } from "@/lib/mistake-name";
import { MarkPill, Pill } from "@/components/shell";
import { held, type CaptureAnswer } from "@/lib/queries-read";
import { changeKey, correctRead, judgeRead, nameMistake } from "../actions";

// A wrong answer no named mistake explains, with Jev's shortlist and every named mistake of its operation
// (`GET /capture/{id}/mistakes`, ADR 0036). The engine down is not the page down: nothing is offered then.
export type Unnamed = { answer: string; shortlist: [string, number][]; options: string[]; why: string };
// The right answer each card prints, as the engine stores it, and who changed it from what (`GET /capture/{id}/keys`).
export type Key = { right: string; was: string | null; by: string | null; at: string | null };
const JUDGED = "a person judges this one";

// What the engine did with this answer, said as a sentence rather than a state name. A teacher
// should never have to learn the word `illegible` to use this screen.
function reading(a: CaptureAnswer): string {
  if (a.human_read !== null) return `You said the child wrote ${a.human_read || "nothing"}.`;
  const reason = a.why ?? "";
  // ADR 0032: a right answer waits until the reader has earned trust on this kind of question; a
  // reading the child's own notebook doubts says why; the second reader's guess says who made it.
  if (reason.includes("until the reader is trusted"))
    return `The reader read ${a.read} and marks it right. This kind of question is not yet trusted (${reason.match(/\(([^)]*)\)$/)?.[1] ?? "not enough checks yet"}), so a person confirms it.`;
  if (reason.startsWith("this child's")) return `The reader read ${a.guess}, but ${reason}.`;
  if (a.guess && a.guess_by)
    return `The reader could not settle this (${reason}). The second reader, shown ${a.guess_by.match(/with (\d+)/)?.[1] ?? "some"} of the child's own answers, reads it as ${a.guess}.`;
  if (held(a))
    return a.answer_state === "blank"
      ? "The reader found nothing written here. Every blank is checked by a person before it counts."
      : `The reader read ${a.read}, a wrong answer. Every wrong answer is checked by a person before it counts.`;
  // No percentage. The engine only stands behind a reading it is sure enough of; printing "82% sure"
  // beside it turned every settled answer into a question for the teacher.
  if (a.answer_state === "written") return `The reader read ${a.read}.`;
  if (a.answer_state === "blank") return "The reader found nothing written here.";
  if (a.answer_state === "not_found") return "The reader could not find this question on the photograph.";
  // A tick or a sentence is never handed to the digit reader: it is the educator's to read, not a failure.
  if (a.answer_state === "for_a_person") return "The reader does not read ticks or sentences. Look at the photograph and say what the child ticked or wrote.";
  // The reader knows WHICH of five things went wrong, and saying so turns "your problem now" into
  // a question the teacher can answer at a glance: an answer under the floor she confirms or
  // corrects, a region holding four numbers for two answers she has to split herself.
  const why = a.why ? ` (${a.why})` : "";
  return `There is writing here that the reader could not make out.${why}`;
}

// One answer: the patch of the photograph it was read from, what the engine made of it, and the
// one thing a person is asked — what the child actually wrote.
export function AnswerCard({
  a,
  paperId,
  names,
  unnamed,
  keyOf,
}: {
  a: CaptureAnswer;
  paperId: string;
  names: Record<string, string>;
  unnamed?: Unnamed;
  keyOf?: Key;
}) {
  const box = a.box?.length === 4 ? `?box=${a.box.join(",")}` : "";
  const value = a.human_read ?? (a.read || a.guess) ?? ""; // a guess is offered back, filled in: one press if it is right
  // A held reading (ADR 0029) is confirmed in "What the child wrote", which keeps the engine's mark and
  // named mistake; a Right/Wrong press would record a judgement and drop both.
  const judged = a.status === "needs_teacher" && !held(a);
  // The right answer as the engine stores it (goals/s26-the-right-answer-shown-and-corrected.yaml): the engine's words
  // for it, or — the engine down — the key the page read itself.
  const right = keyOf?.right ?? a.answer ?? JUDGED;
  const changeable = right !== JUDGED && !right.startsWith("any answer that makes");
  return (
    <li id={`a-${a.id}`} className="grid scroll-mt-6 gap-3 border border-basalt/12 p-4 md:grid-cols-[300px_minmax(0,1fr)]">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={`/api/scan/${a.capture_id}/${a.file_page}${box}`}
        alt={`What the child wrote for question ${a.slot}`}
        className="max-h-[170px] w-full border border-basalt/14 bg-chalk object-contain"
      />
      <div className="min-w-0">
        <div className="flex flex-wrap items-baseline gap-x-3">
          <span className="label">Question {a.slot}</span>
          {a.part ? <span className="text-[12.5px] text-basalt/70">{a.part}</span> : null}
          <MarkPill status={a.status} working={a.working_shown === "none" ? "" : a.working_shown} />
          {a.state === "confirmed" ? <Pill tone="neem">signed off</Pill> : null}
          {a.human_read !== null ? <span className="text-[12px] text-basalt/55">corrected by {a.corrected_by}</span> : null}
        </div>
        <div className="mt-1 text-[14px] leading-snug">{a.question}</div>
        <p className="mt-1 text-[13.5px]">
          <span className="label">Right answer</span> <strong>{right}</strong>
          {keyOf?.by ? (
            <span className="text-[12px] text-basalt/55"> · changed from {keyOf.was ?? "none"} by {keyOf.by}</span>
          ) : null}
        </p>
        <p className="mt-2 text-[13.5px]">{reading(a)}</p>
        {a.misconception_codes.length ? (
          <p className="mt-1 text-[12.5px] text-terracotta">
            The mistake this matches: {a.misconception_codes.map((c) => mistakeName(names, c, a.op, a.mistake_skills?.[c] ?? a.skill_code)).join("; ")}
            <span className="fact ml-2 text-[11px] text-basalt/45">{a.misconception_codes.join(" ")}</span>
          </p>
        ) : null}
        {unnamed && a.state !== "confirmed" ? <MistakePicker a={a} paperId={paperId} names={names} u={unnamed} /> : null}
        {a.state === "confirmed" ? (
          // A paper signed off by mistake is put right here: the answer is marked again and its evidence replaced by
          // a new batch in your name; the old one is kept (migration 20261015090000).
          <details className="mt-3">
            <summary className="cursor-pointer text-[12.5px] text-basalt/60">Signed off wrongly? Correct what the child wrote</summary>
            <form action={correctRead} className="mt-2 flex flex-wrap items-end gap-2">
              <input type="hidden" name="result_id" value={a.id} />
              <input type="hidden" name="paper_id" value={paperId} />
              <label className="field">
                <span className="label">What the child wrote</span>
                <input className="input w-[150px]" name="human_read" defaultValue={value} placeholder="leave empty for blank" />
              </label>
              <button className="btn secondary" type="submit">Save the correction</button>
            </form>
          </details>
        ) : (
          <>
            <form action={correctRead} className="mt-3 flex flex-wrap items-end gap-2">
              <input type="hidden" name="result_id" value={a.id} />
              <input type="hidden" name="paper_id" value={paperId} />
              <label className="field">
                <span className="label">What the child wrote</span>
                <input className="input w-[150px]" name="human_read" defaultValue={value} placeholder="leave empty for blank" />
              </label>
              <button className="btn secondary" type="submit">Save</button>
            </form>
            {judged ? (
              <form action={judgeRead} className="mt-2 flex flex-wrap items-center gap-2">
                <input type="hidden" name="result_id" value={a.id} />
                <input type="hidden" name="paper_id" value={paperId} />
                <span className="note">The engine cannot mark this one — only you can say:</span>
                <button className="btn secondary" name="status" value="correct" type="submit">Right</button>
                <button className="btn secondary" name="status" value="wrong" type="submit">Wrong</button>
                <button className="btn secondary" name="status" value="blank" type="submit">Blank</button>
              </form>
            ) : null}
          </>
        )}
        {changeable ? (
          // An educator who finds the stored right answer wrong changes it here, for every child (ADR 0045). Code checks
          // it first — a sum's right answer is its arithmetic — and says why when it refuses.
          <details className="mt-3">
            <summary className="cursor-pointer text-[12.5px] text-basalt/60">
              Is the right answer wrong? Change it for every child
            </summary>
            <form action={changeKey} className="mt-2 flex flex-wrap items-end gap-2">
              <input type="hidden" name="result_id" value={a.id} />
              <input type="hidden" name="paper_id" value={paperId} />
              <input type="hidden" name="slot" value={a.slot} />
              <label className="field">
                <span className="label">The right answer is</span>
                <input className="input w-[150px]" name="answer" defaultValue={right} required />
              </label>
              <button className="btn secondary" type="submit">Change it for every child</button>
            </form>
            <p className="note mt-1">
              Every child&rsquo;s answer to question {a.slot} is marked again with it, signed off or not; a signed-off
              answer gets new evidence and keeps the old.
            </p>
          </details>
        ) : null}
      </div>
    </li>
  );
}

// Wrong, and in a way no named mistake reproduces (goals/j2-name-the-mistake.yaml): Jev's three likeliest are one press
// each, any other named mistake is in the list, and "none of these" is an answer too. Jev only proposes.
function MistakePicker({ a, paperId, names, u }: { a: CaptureAnswer; paperId: string; names: Record<string, string>; u: Unnamed }) {
  const listed = new Set(u.shortlist.map(([c]) => c));
  const label = (c: string) => (c === "NONE" ? "None of these" : mistakeName(names, c, a.op, a.mistake_skills?.[c] ?? a.skill_code));
  return (
    <div className="mt-3 border-l-2 border-terracotta/40 pl-3" aria-label={`Name the mistake for question ${a.slot}`}>
      <p className="text-[12.5px]">
        No named mistake makes {u.answer}. {u.shortlist.length ? "The likeliest, from Jev — you decide:" : u.why || "Which is it?"}
      </p>
      <form action={nameMistake} className="mt-2 flex flex-wrap items-center gap-2">
        <input type="hidden" name="result_id" value={a.id} />
        <input type="hidden" name="paper_id" value={paperId} />
        <input type="hidden" name="proposed" value={JSON.stringify(u.shortlist)} />
        {u.shortlist.map(([c, p]) => (
          <button key={c} className="btn secondary" name="code" value={c} type="submit">
            {label(c)} <span className="text-[11px] text-basalt/55">{Math.round(p * 100)}%</span>
          </button>
        ))}
        {listed.has("NONE") ? null : (
          <button className="btn secondary" name="code" value="NONE" type="submit">None of these</button>
        )}
      </form>
      <form action={nameMistake} className="mt-2 flex flex-wrap items-center gap-2">
        <input type="hidden" name="result_id" value={a.id} />
        <input type="hidden" name="paper_id" value={paperId} />
        <input type="hidden" name="proposed" value={JSON.stringify(u.shortlist)} />
        <select className="select" name="code" aria-label={`Another mistake for question ${a.slot}`} defaultValue="">
          <option value="" disabled>Another named mistake…</option>
          {u.options.filter((c) => !listed.has(c) && c !== "NONE").map((c) => (
            <option key={c} value={c}>{label(c)}</option>
          ))}
        </select>
        <button className="btn secondary" type="submit">Name it</button>
      </form>
    </div>
  );
}
