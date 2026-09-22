import Link from "@/components/link";
import { Bar, Body, Notice, PageHeader, Panel } from "@/components/shell";
import { requireStaff } from "@/lib/auth";
import { deadline } from "@/lib/deadline";
import { checkItem, checkQueue, held, toJudge, type CheckItem } from "@/lib/queries-read";
import { correctRead, judgeOne } from "../actions";

type Props = { searchParams: Promise<Record<string, string | undefined>> };

const fmtDate = (d: string | null) =>
  d ? new Date(d).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }).replace(/ /g, "-") : "—";

// Why the engine is asking, in a sentence a teacher can act on — never the reader's own vocabulary.
function whyHere(a: CheckItem, spot: boolean): string {
  if (spot) return "A spot-check: the engine was sure of this one. Say whether it read it right.";
  const reason = a.why ?? "";
  // ADR 0032: a right answer waits until the reader has earned trust on this kind of question, and a
  // reading the child's own notebook doubts is offered back with its reason.
  if (reason.includes("until the reader is trusted"))
    return `The reader read it as a right answer. This kind of question is not yet trusted (${reason.match(/\(([^)]*)\)$/)?.[1] ?? "not enough checks yet"}), so say whether it read it right.`;
  if (reason.startsWith("this child's")) return `The reader read it, but ${reason}.`;
  if (held(a))
    return a.answer_state === "blank"
      ? "The engine found nothing written here. Every blank is checked by a person before it counts."
      : "The engine read this as a wrong answer. Every wrong answer is checked by a person before it counts.";
  if (toJudge(a)) return "The reader read it, but only a person can say whether it is right.";
  if (a.answer_state === "not_found") return "The reader could not find this question on the photograph, so the whole page is shown.";
  const why = a.why ?? "";
  if (why.includes("numbers in the region"))
    return "The reader found a different number of numbers here than the question has answers.";
  if (why.includes("not a number"))
    return "The answer is not a number, so the reader leaves it to you. Type it the way the paper asks for it: the numbers in order, the sign, or the word the child chose.";
  if (why.includes("no number")) return "There is writing here, but no number the reader could make out.";
  if (why.includes("paper printed")) return "The only numbers here are the question's own; the child may have left it blank.";
  return "The reader could not be sure what the child wrote.";
}

// Every answer the engine is unsure of, one at a time: the child's own writing, the question, the
// reader's best guess. A person settles it in a click and the next one appears (Nimish: "I'm not even
// able to see what all validations you need from our side"). The engine marks what the person says.
export default async function CheckAnswers({ searchParams }: Props) {
  const me = await requireStaff();
  const q = await searchParams;
  const queue = await deadline(checkQueue());
  // ?id= opens one answer where it stands in the queue; ?from= keeps the place after an answer is settled.
  const at = q.id ? queue.findIndex((e) => e.id === q.id) : -1;
  const from = at >= 0 ? at : Math.min(Math.max(0, Number(q.from) || 0), Math.max(0, queue.length - 1));
  const entry = queue[from];
  const a = entry ? await deadline(checkItem(entry.id, me.email)) : undefined;
  const waiting = queue.filter((e) => !e.spot).length;
  const spots = queue.length - waiting;
  const next = `/capture/check?from=${from}`;
  const box = a?.box?.length === 4 && a.answer_state !== "not_found" ? `?box=${a.box.join(",")}` : "";

  return (
    <>
      <PageHeader
        stage="Stage 3 · Read"
        title="Check the answers"
        sub="Every answer the engine was not sure of, one at a time, with the child's own writing. Say what the child wrote; the engine marks it."
      />
      <Body>
        {q.error === "engine" ? (
          <Notice tone="terracotta">The engine could not be reached, so that answer was not saved. Try it again.</Notice>
        ) : null}
        <div className="mb-[18px] grid gap-2">
          <p className="text-[14px]">
            <strong>{waiting}</strong> {waiting === 1 ? "answer" : "answers"} left to check · {spots} spot-
            {spots === 1 ? "check" : "checks"} · answer {queue.length ? from + 1 : 0} of {queue.length}
          </p>
          <Bar tone="neem" share={queue.length ? from / queue.length : 1} width={320} />
        </div>

        {!a || !entry ? (
          <Notice tone="neem">
            Nothing is waiting. Every answer the engine read is settled — by the engine or by a person.
          </Notice>
        ) : (
          <Panel
            title={`${a.first_name} · question ${a.slot}`}
            aside={`${a.paper_title ?? "paper"} · sat ${fmtDate(a.sat)}`}
          >
            <div className="grid gap-[18px] lg:grid-cols-[minmax(0,1fr)_380px]">
              <figure className="min-w-0">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={`/api/scan/${a.capture_id}/${a.page}${box}`}
                  alt={`What ${a.first_name} wrote for question ${a.slot}`}
                  className="max-h-[420px] w-full border border-basalt/14 bg-chalk object-contain"
                />
                <figcaption className="note mt-1">
                  {box ? "The part of the page the answer was read from." : `Page ${a.page}, as it was photographed.`}{" "}
                  <Link href={`/capture/${a.paper_id}#a-${a.id}`}>Open the whole paper →</Link>
                </figcaption>
              </figure>

              <div className="grid content-start gap-3 text-[14px]">
                <div>
                  <span className="label">The question</span>
                  <p className="mt-1 leading-snug">{a.question}</p>
                </div>
                <p className="note">{whyHere(a, entry.spot)}</p>

                {entry.spot ? (
                  <p>
                    The engine read <strong className="fact">{a.read || "nothing"}</strong>.
                  </p>
                ) : a.guess && a.guess_by ? (
                  <p>
                    The second reader, shown {a.guess_by.match(/with (\d+)/)?.[1] ?? "some"} of the child&rsquo;s own answers, thinks the child wrote{" "}
                    <strong className="fact">{a.guess}</strong>.
                  </p>
                ) : a.guess ? (
                  <p>
                    The reader thinks the child wrote <strong className="fact">{a.guess}</strong>.
                  </p>
                ) : null}

                {toJudge(a) ? (
                  <>
                    <form action={judgeOne} className="flex flex-wrap items-center gap-2">
                      <input type="hidden" name="result_id" value={a.id} />
                      <input type="hidden" name="paper_id" value={a.paper_id} />
                      <input type="hidden" name="next" value={next} />
                      <span>
                        The child wrote <strong className="fact">{a.human_read ?? a.read}</strong>. Is it
                      </span>
                      <button className="btn" name="status" value="correct" type="submit">
                        Right
                      </button>
                      <button className="btn secondary" name="status" value="wrong" type="submit">
                        Wrong
                      </button>
                      <button className="btn secondary" name="status" value="blank" type="submit">
                        Blank
                      </button>
                    </form>
                    {/* A judgement says whether the child is right, not what the child wrote: when the
                        reading itself is wrong, it is corrected here and the engine marks it again. */}
                    <form action={correctRead} className="flex flex-wrap items-end gap-2">
                      <input type="hidden" name="result_id" value={a.id} />
                      <input type="hidden" name="paper_id" value={a.paper_id} />
                      <input type="hidden" name="next" value={next} />
                      <label className="field">
                        <span className="label">Not what the child wrote? Type it</span>
                        <input className="input w-[160px]" name="human_read" required maxLength={40} />
                      </label>
                      <button className="btn secondary" type="submit">
                        Save
                      </button>
                    </form>
                  </>
                ) : (
                  <>
                    {entry.spot || a.guess ? (
                      <form action={correctRead}>
                        <input type="hidden" name="result_id" value={a.id} />
                        <input type="hidden" name="paper_id" value={a.paper_id} />
                        <input type="hidden" name="next" value={next} />
                        <input type="hidden" name="human_read" value={(entry.spot ? a.read : a.guess) ?? ""} />
                        <button className="btn" type="submit">
                          Yes, the child wrote {(entry.spot ? a.read : a.guess) || "nothing"}
                        </button>
                      </form>
                    ) : null}
                    <form action={correctRead} className="flex flex-wrap items-end gap-2">
                      <input type="hidden" name="result_id" value={a.id} />
                      <input type="hidden" name="paper_id" value={a.paper_id} />
                      <input type="hidden" name="next" value={next} />
                      <label className="field">
                        <span className="label">{entry.spot || a.guess ? "No — the child wrote" : "What the child wrote"}</span>
                        <input className="input w-[160px]" name="human_read" required maxLength={40} />
                      </label>
                      <button className="btn secondary" type="submit">
                        Save
                      </button>
                    </form>
                    <form action={correctRead}>
                      <input type="hidden" name="result_id" value={a.id} />
                      <input type="hidden" name="paper_id" value={a.paper_id} />
                      <input type="hidden" name="next" value={next} />
                      <input type="hidden" name="human_read" value="" />
                      <button className="btn secondary" type="submit">
                        Nothing is written here
                      </button>
                    </form>
                  </>
                )}

                <div className="flex flex-wrap gap-3 pt-2 text-[13px]">
                  {from > 0 ? <Link href={`/capture/check?from=${from - 1}`}>← Previous</Link> : null}
                  {from + 1 < queue.length ? <Link href={`/capture/check?from=${from + 1}`}>Later — show the next one →</Link> : null}
                </div>
                <p className="note">
                  Your answer is saved in your name and the engine marks it; what the engine read first is kept beside it, so
                  the reader can be measured against you.
                </p>
              </div>
            </div>
          </Panel>
        )}
      </Body>
    </>
  );
}
