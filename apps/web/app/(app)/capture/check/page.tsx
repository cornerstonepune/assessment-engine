import Link from "@/components/link";
import { Count } from "@/components/count";
import { EmptyState } from "@/components/empty-state";
import { PageShell } from "@/components/page-shell";
import { Bar, Notice, Panel } from "@/components/shell";
import { StatusChip } from "@/components/status-chip";
import { requireStaff } from "@/lib/auth";
import { scopeOf } from "@/lib/scope";
import { deadline } from "@/lib/deadline";
import { checkItem, checkQueue, held, toJudge, type CheckItem } from "@/lib/queries-read";
import { EngineDown, engineGet } from "@/lib/engine";
import { Confirm, Judge, Nothing, TypeIt } from "./answer";
import { ZoomPage } from "./zoom-page";
import type { Key } from "../[id]/card";
import { dateWords } from "@/lib/week";

type Props = { searchParams: Promise<Record<string, string | undefined>> };


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

// The right answer this answer is marked against, as the engine stores it (`GET /capture/{id}/keys`, goals/s26-the-
// right-answer-shown-and-corrected.yaml). The engine down, the key the queue read itself.
async function keyOf(paper: string, id: string): Promise<Key | undefined> {
  try {
    const res = await engineGet(`/capture/${paper}/keys`);
    return res.ok ? ((await res.json()) as Record<string, Key>)[id] : undefined;
  } catch (e) {
    if (e instanceof EngineDown) return undefined;
    throw e;
  }
}

// Every answer the engine is unsure of, one at a time: the child's own writing, the question, the
// reader's best guess. A person settles it in a click and the next one appears (Nimish: "I'm not even
// able to see what all validations you need from our side"). The engine marks what the person says.
export default async function CheckAnswers({ searchParams }: Props) {
  const me = await requireStaff();
  const q = await searchParams;
  const queue = await deadline(checkQueue(scopeOf(me)));
  // ?id= opens one answer where it stands in the queue; ?from= keeps the place after an answer is settled.
  const at = q.id ? queue.findIndex((e) => e.id === q.id) : -1;
  const from = at >= 0 ? at : Math.min(Math.max(0, Number(q.from) || 0), Math.max(0, queue.length - 1));
  const entry = queue[from];
  const a = entry ? await deadline(checkItem(entry.id, me.email)) : undefined;
  const key = a ? await keyOf(a.paper_id, a.id) : undefined;
  const waiting = queue.filter((e) => !e.spot).length;
  const spots = queue.length - waiting;
  const next = `/capture/check?from=${from}`;
  const box = a?.box?.length === 4 && a.answer_state !== "not_found" ? `?box=${a.box.join(",")}` : "";

  const says = entry?.spot ? (a?.read ?? "") : (a?.guess ?? "");
  return (
    <PageShell
      stage="Assessments · check answers"
      title="Check the answers"
      purpose="Every answer the engine was not sure of, one at a time, with the child's own writing. Say what the child wrote; the engine marks it."
      action={
      <div className="grid gap-2">
        <p className="text-[14px]">
          <Count of="answers to check" n={waiting} /> {waiting === 1 ? "answer" : "answers"} left to check · {spots} spot-
          {spots === 1 ? "check" : "checks"} · answer {queue.length ? from + 1 : 0} of {queue.length}
        </p>
        <Bar tone="neem" share={queue.length ? from / queue.length : 1} width={320} />
      </div>
      }
      next={from + 1 < queue.length ? { href: `/capture/check?from=${from + 1}`, label: "Later — show the next one" } : { href: "/growth", label: "See the class results" }}
    >
      <p className="mb-4">
        <Link href="/capture" className="chip">
          ← Marking
        </Link>
      </p>
      {q.error === "engine" ? (
        <Notice tone="terracotta">The engine could not be reached, so that answer was not saved. Try it again.</Notice>
      ) : null}

      {!a || !entry ? (
        <EmptyState>Nothing is waiting. Every answer the engine read is settled — by the engine or by a person.</EmptyState>
      ) : (
        <Panel
          title={`${a.first_name} · question ${a.slot}`}
          aside={
            <>
              <StatusChip state={entry.spot ? "spot" : toJudge(a) ? "judge" : "waiting"} />{" "}
              {`${a.paper_title ?? "paper"}${a.sat ? ` · sat ${dateWords(a.sat)}` : ""}`}
            </>
          }
        >
          <div className="grid gap-[18px] lg:grid-cols-[minmax(0,1fr)_380px]">
            <figure className="min-w-0">
              <p className="mb-2 text-[15px] leading-snug">
                <strong>Question {a.slot}</strong> · {a.question}
              </p>
              {box ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={`/api/scan/${a.capture_id}/${a.file_page}${box}`}
                  alt={`What ${a.first_name} wrote for question ${a.slot}`}
                  className="max-h-[560px] w-full border border-basalt/14 bg-chalk object-contain"
                />
              ) : (
                <ZoomPage
                  src={`/api/scan/${a.capture_id}/${a.file_page}`}
                  alt={`What ${a.first_name} wrote for question ${a.slot}`}
                />
              )}
              <figcaption className="note mt-1">
                {box
                  ? `The part of page ${a.page} that is question ${a.slot}.`
                  : `We could not find question ${a.slot} on this page: it is somewhere on this page. Click the page to enlarge it.`}{" "}
                <Link href={`/capture/${a.paper_id}#a-${a.id}`}>Open the whole paper →</Link>
              </figcaption>
            </figure>

            <div className="grid content-start gap-3 text-[14px]">
              <div>
                <span className="label">The question</span>
                {a.part ? <span className="ml-2 text-[12.5px] text-basalt/70">{a.part}</span> : null}
                <p className="mt-1 leading-snug">{a.question}</p>
                <p className="mt-1">
                  <span className="label">Right answer</span>{" "}
                  <strong className="fact">{key?.right ?? a.answer ?? "a person judges this one"}</strong>
                  {key?.by ? <span className="text-[12px] text-basalt/55"> · changed from {key.was ?? "none"} by {key.by}</span> : null}
                </p>
              </div>
              <p className="note">{whyHere(a, entry.spot)}</p>

              {entry.spot ? (
                <p>
                  The engine read <strong className="fact">{a.read || "nothing"}</strong>.
                </p>
              ) : a.second_read !== null ? (
                <p>
                  Two readers disagree. The reader thinks the child wrote <strong className="fact">{a.guess}</strong>; the second reader, shown the child&rsquo;s own answers, reads <strong className="fact">{a.second_read || "nothing"}</strong>. Look at the photograph.
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

              {/* the decision sits in the box with the sentence it answers */}
              {toJudge(a) ? (
                // A judgement says whether the child is right, not what the child wrote: when the reading itself is
                // wrong, it is corrected here and the engine marks it again.
                <>
                  <Judge a={a} next={next} />
                  <TypeIt a={a} next={next} label="Not what the child wrote? Type it" />
                </>
              ) : (
                <>
                  {entry.spot || a.guess ? <Confirm a={a} next={next} says={says} /> : null}
                  {entry.spot || a.guess ? <TypeIt a={a} next={next} label="No — the child wrote" /> : null}
                  {!entry.spot && !a.guess ? <TypeIt a={a} next={next} label="What the child wrote" primary /> : null}
                  <Nothing a={a} next={next} />
                </>
              )}

              <div className="flex flex-wrap gap-3 pt-2 text-[13px]">
                {from > 0 ? <Link href={`/capture/check?from=${from - 1}`}>← Previous</Link> : null}
              </div>
              <p className="note">
                Your answer is saved in your name and the engine marks it; what the engine read first is kept beside it, so
                the reader can be measured against you.
              </p>
            </div>
          </div>
        </Panel>
      )}
    </PageShell>
  );
}
