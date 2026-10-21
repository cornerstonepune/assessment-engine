import Link from "@/components/link";
import { Body, PageHeader } from "@/components/shell";
import { requireStaff } from "@/lib/auth";
import { scopeOf } from "@/lib/scope";
import { deadline } from "@/lib/deadline";
import { kindWords } from "@/components/question";
import { questionKinds } from "@/lib/question-types";
import { type Line, needsYou, TODAY_ORDER } from "@/lib/needs-you";
import { queueByWeek, type Trust, trustNow, type Week } from "@/lib/queries-today";
import { weekWords } from "@/lib/week";

// Today — everything that waits on a person, in one list under the tab where it is done (goals/ui1-menu-and-today.yaml,
// goals/u1-today.yaml), each line opening that place. The menu's counts are this list's (lib/needs-you.ts). Every line
// is the signed-in person's: in their classes, and only where the decision is theirs (goals/ux1-who-sees-what.yaml). The
// engine proposes; a person approves.
export default async function Today() {
  const me = await requireStaff();
  const scope = scopeOf(me);
  const [lines, weeks, trust, { words }] = await deadline(Promise.all([needsYou(me), queueByWeek(), trustNow(), questionKinds()]));
  return (
    <>
      <PageHeader stage="Today" title="Today" sub="Everything that waits on a person, under the tab where it is done. Each line opens the place to do it." />
      <Body>
        {scope.note ? (
          <p role="status" className="note mb-5">
            {scope.note}
          </p>
        ) : null}
        {TODAY_ORDER.map((tab) => (
          <section key={tab} aria-label={tab} className="mb-6">
            <h2 className="label mb-2">{tab}</h2>
            {lines[tab].length ? (
              <div className="panel divide-y divide-basalt/12">{lines[tab].map((l) => <Row key={l.title} line={l} />)}</div>
            ) : (
              <p className="note">Nothing waits here.</p>
            )}
          </section>
        ))}
        <Shrinking weeks={weeks} trust={trust} words={words} />
      </Body>
    </>
  );
}

// the first few of a line's items, each its own link; the rest are where the line's `more` lists them all
// (goals/ui6b-no-long-lists.yaml): a parent report waiting for each of 170 children was 170 links on Today
const FIRST = 5;

/** One kind of thing that waits: how many, what it is, and where it is done — or, for class packs and parent reports,
 *  each one of them as its own link. */
function Row({ line }: { line: Line }) {
  return (
    <section data-testid="line" data-waits={line.waits ? "yes" : "no"} aria-label={line.title} className="grid gap-x-4 gap-y-1 p-4 md:grid-cols-[64px_minmax(0,1fr)_auto] md:items-start">
      <span data-testid="count" className={`font-heading text-[26px] leading-none tabular-nums ${line.waits ? "" : "text-basalt/55"}`}>
        {line.n.toLocaleString("en-IN")}
      </span>
      <div className="min-w-0">
        <h3 className="font-heading text-[16.5px]">{line.title}</h3>
        <p className="text-[13px] text-basalt/70">{line.words}</p>
        {line.items?.length ? (
          <ul className="mt-2 grid gap-1 text-[13.5px]">
            {line.items.slice(0, FIRST).map((it) => (
              <li key={it.href}>
                <Link href={it.href}>{it.label}</Link>
                {it.n ? <span className="text-basalt/62"> — {it.n} {it.n === 1 ? "paper" : "papers"}</span> : null}
              </li>
            ))}
            {line.items.length > FIRST && line.more ? (
              <li>
                <Link href={line.more}>and {line.items.length - FIRST} more →</Link>
              </li>
            ) : null}
          </ul>
        ) : null}
      </div>
      {line.href && line.action ? (
        <Link href={line.href} className={`btn self-start ${line.waits ? "" : "secondary"}`}>
          {line.action}
        </Link>
      ) : null}
    </section>
  );
}

// Whether checking pays (goals/ny2-the-queue-shrinks.yaml): each week's answers, how many a person had to check, and how
// near the reader is to settling a kind of question alone. Every wrong and blank still waits for a person (ADR 0029).
function Shrinking({ weeks, trust, words }: { weeks: Week[]; trust: Trust; words: Record<string, string> }) {
  const title = "Is the queue shrinking?";
  return (
    <section aria-label={title} className="panel mb-6 p-4">
      <h2 className="font-heading text-[17px]">{title}</h2>
      <p className="mt-1 text-[13.5px] leading-snug">
        The reader is trusted on {trust.kinds ? `${trust.trusted} of ${trust.kinds}` : "none of the"} kinds of question it has read
        {trust.nearest ? `; the nearest, ${kindWords(words, trust.nearest.fmt)}, needs ${trust.nearest.to_trust} more right ${trust.nearest.to_trust === 1 ? "check" : "checks"}` : ""}. A trusted kind&apos;s
        right answers settle without a person; every wrong and every blank still waits for one.
      </p>
      {weeks.length ? (
        <div className="mt-3 min-w-0 overflow-x-auto">
          <table className="grid" aria-label="Answers read, week by week">
            <thead>
              <tr>
                <th>Week</th>
                <th className="num">Answers read</th>
                <th className="num">Settled by the engine alone</th>
                <th className="num">Checked by a person</th>
                <th className="num">Still waiting</th>
                <th className="num">Needed a person</th>
              </tr>
            </thead>
            <tbody>
              {weeks.map((k) => (
                <tr key={k.week}>
                  <td className="fact whitespace-nowrap">{weekWords(k.week)}</td>
                  <td className="num">{k.read}</td>
                  <td className="num">{k.alone}</td>
                  <td className="num">{k.person}</td>
                  <td className="num">{k.waiting}</td>
                  <td className="num">{Math.round((100 * (k.person + k.waiting)) / k.read)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="note mt-2">No papers read yet.</p>
      )}
    </section>
  );
}
