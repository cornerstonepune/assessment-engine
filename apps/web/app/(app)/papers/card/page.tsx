import Link from "@/components/link";
import { Body, Notice, PageHeader, Panel } from "@/components/shell";
import { requireStaff } from "@/lib/auth";
import { deadline } from "@/lib/deadline";
import { classWords } from "@/lib/needs-you";
import { grades } from "@/lib/queries";
import { assessmentCard, CARD_STAGES, type Card, type CardCopy, type CardKey, standing } from "@/lib/queries-card";
import { KIND_WORDS, STAGE_WORDS } from "@/lib/queries-papers";
import { dateWords, weekWords } from "@/lib/week";
import { UploadScans } from "../../capture/upload-scans";
import { away, givenOn } from "./actions";

type Props = { searchParams: Promise<Record<string, string | undefined>> };

// One assessment as one card (goals/s2-the-assessment-card.yaml), from the scope Nimish locked on 2026-10-22: Made →
// approved for print → Given → Papers in → Read → Checked → Signed off → Results, always showing its next step. The
// upload box is at the top: a page goes where its printed code says, whichever card it is put in from. Every member of
// staff sees every card (goals/ux9c-one-role.yaml).
export default async function CardPage({ searchParams }: Props) {
  const me = await requireStaff();
  const q = await searchParams;
  const key: CardKey = { class: q.class ?? "", week: q.week ?? "", kind: q.kind ?? "", set: q.set || undefined };
  const [card, g] = await deadline(Promise.all([assessmentCard(key, me.email), grades()]));
  const title = card.copies[0]?.title ?? card.spares[0]?.title ?? "No such assessment";
  const band = card.copies[0]?.band ?? card.spares[0]?.band;
  const s = standing(card);
  return (
    <>
      <PageHeader
        stage="Assessments · its card"
        title={key.kind === "focus" ? "Home assessments" : title}
        sub={`${KIND_WORDS[key.kind] ?? key.kind} · ${band ? classWords(g, band, key.class) : key.class} · ${weekWords(key.week || null)}`}
      />
      <Body>
        {q.said ? <Notice tone="terracotta">{q.said}</Notice> : null}
        {s.n === 0 ? (
          <p className="note">No paper of this class, week and kind was found: open it from Assessments.</p>
        ) : (
          <div className="grid min-w-0 gap-[18px]">
            <Panel title="Papers in" label="Papers in" aside={`${s.inn} of ${s.n} in`}>
              <UploadScans reading={!!card.reading} />
              <p className="mt-2 text-[13px] text-basalt/70">
                Put in the scan or the photos of any papers: each page goes where its printed code says, whichever card you put it in from.
              </p>
            </Panel>
            <Stages at={s.at} done={s.done} />
            <Next card={card} s={s} />
            <Copies card={card} />
          </div>
        )}
      </Body>
    </>
  );
}

type Standing = ReturnType<typeof standing>;

function Stages({ at, done }: { at: Standing["at"]; done: Standing["done"] }) {
  return (
    <ol aria-label="Where it stands" className="flex flex-wrap gap-1 text-[12.5px]">
      {CARD_STAGES.map((st, i) => (
        <li
          key={st}
          aria-current={st === at ? "step" : undefined}
          className={`border px-2 py-1 ${st === at ? "border-terracotta bg-terracotta/12 font-semibold" : done[st] ? "border-neem/40 bg-neem/10" : "border-basalt/15 text-basalt/55"}`}
        >
          {i + 1}. {st}
          {done[st] && st !== at ? " ✓" : ""}
        </li>
      ))}
    </ol>
  );
}

const rollsSaid = (cs: CardCopy[]) => cs.map((c) => (c.roll_no ? `roll ${c.roll_no}` : c.qr)).join(", ");

/** The one next step for where the card stands, and what the card knows at that stage. */
function Next({ card, s }: { card: Card; s: Standing }) {
  const { key } = card;
  // the school's day, as the engine checks it: "2026-10-22" in Pune, whatever the server's clock
  const today = new Date().toLocaleDateString("en-CA", { timeZone: "Asia/Kolkata" });
  const retake = card.copies.filter((c) => c.retake.length);
  return (
    <Panel title={`Next: ${s.at}`} label="Next step">
      <ul className="mb-3 grid gap-1 text-[14px]">
        <li>
          {s.n} {s.n === 1 ? "paper" : "papers"} made{card.spares.length ? `, and ${card.spares.length} spare` : ""}; {s.approved} approved for print.
        </li>
        <li data-testid="given">
          {card.given ? `Given on ${dateWords(card.given.on)}, said by ${card.given.by}.` : s.inn ? "Papers are in, so it was given; no one said the day." : "Not said to be given yet."}
        </li>
        <li data-testid="in">
          {s.inn} of {s.n} in{s.out.length ? ` · missing: ${rollsSaid(s.out)}` : ""}
          {s.away.length ? ` · away, held for later: ${rollsSaid(s.away)}` : ""}
        </li>
        {card.reading ? (
          <li data-testid="reading">
            Reading a file now: page {card.reading.pages} of {card.reading.of}
            {card.reading.minutes ? `, about ${card.reading.minutes} ${card.reading.minutes === 1 ? "minute" : "minutes"} left` : ""}.
          </li>
        ) : null}
        {s.inn ? (
          <li>
            {s.checked} of {s.inn} checked{s.waiting ? ` · ${s.waiting} ${s.waiting === 1 ? "answer waits" : "answers wait"} for a person` : ""}; {s.signed} signed off.
          </li>
        ) : null}
      </ul>
      {retake.length ? (
        <div role="alert" aria-label="To photograph again" className="mb-3 border border-terracotta/30 bg-terracotta/10 p-3 text-[13.5px]">
          <p className="font-semibold">To photograph again</p>
          <ul className="ml-5 list-disc">
            {retake.map((c) => (
              <li key={c.qr}>
                {c.roll_no ? `Roll ${c.roll_no}` : c.qr}: {c.retake.join("; ")}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      {s.at === "Made" || s.at === "Approved for print" ? (
        <p className="text-[13.5px]">
          The system proposed each child&apos;s paper; change any child before it prints.{" "}
          <Link className="btn" href={key.kind === "focus" ? `/make/${encodeURIComponent(key.class)}` : `/papers/approve?section=${encodeURIComponent(key.class)}&week=${encodeURIComponent(key.week)}&kind=${key.kind}`}>
            Look over and approve for print →
          </Link>
        </p>
      ) : null}
      {s.at === "Given" ? (
        <form action={givenOn} className="flex flex-wrap items-end gap-2">
          <Back k={key} />
          {[...card.copies, ...card.spares].map((c) => (
            <input key={c.qr} type="hidden" name="qr" value={c.qr} />
          ))}
          <label className="field">
            <span className="label">Day it was given</span>
            <input className="input" type="date" name="on" defaultValue={today} max={today} required />
          </label>
          <button type="submit" className="btn">
            Given on
          </button>
        </form>
      ) : null}
      {s.at === "Papers in" || s.at === "Read" ? <p className="text-[13.5px]">Put the papers in at the top of this card. A child who was away is marked below; their paper is held for later, not missing.</p> : null}
      {s.at === "Checked" ? (
        <Link className="btn" href="/capture/check">
          Check them →
        </Link>
      ) : null}
      {s.at === "Signed off" ? (
        <Link className="btn" href={`/capture?by=child&class=${encodeURIComponent(key.class)}`}>
          Sign them off →
        </Link>
      ) : null}
      {s.at === "Results" ? <p className="text-[13.5px]">Every paper is signed off: each child&apos;s score is below, and each child opens their profile.</p> : null}
    </Panel>
  );
}

/** The card's own fields, so an action comes back to it. */
function Back({ k }: { k: CardKey }) {
  return (
    <>
      <input type="hidden" name="class" value={k.class} />
      <input type="hidden" name="week" value={k.week} />
      <input type="hidden" name="kind" value={k.kind} />
      {k.set ? <input type="hidden" name="set" value={k.set} /> : null}
    </>
  );
}

function Copies({ card }: { card: Card }) {
  return (
    <Panel title="Each child's paper" label="Each child's paper">
      <div className="min-w-0 overflow-x-auto">
        <table className="grid" aria-label="Each child's paper">
          <thead>
            <tr>
              <th>Roll</th>
              <th>Child</th>
              <th>Paper</th>
              <th>Where it is</th>
              <th className="num">Score</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {card.copies.map((c) => {
              const out = ["made", "printed"].includes(c.stage);
              return (
                <tr key={c.qr} data-roll={c.roll_no ?? ""}>
                  <td className="fact">{c.roll_no ?? "—"}</td>
                  <td>{c.child_id ? <Link href={`/growth/${c.child_id}`}>{c.child ?? "this child"}</Link> : "spare"}</td>
                  <td>
                    {c.title}
                    <span className="block text-[11.5px] text-basalt/55">
                      code <Link href={`/worksheets/${c.qr}`}>{c.qr}</Link>
                    </span>
                  </td>
                  <td>{c.away && out ? "away · held for later" : STAGE_WORDS[c.stage]}</td>
                  <td className="num">{c.scored ? `${c.right} of ${c.scored}` : "—"}</td>
                  <td>
                    {out && c.printed ? (
                      <form action={away}>
                        <Back k={card.key} />
                        <input type="hidden" name="qr" value={c.qr} />
                        <input type="hidden" name="away" value={c.away ? "no" : "yes"} />
                        <button type="submit" className="btn secondary whitespace-nowrap text-[12.5px]">
                          {c.away ? "Back: count as missing" : "Away: hold it for later"}
                        </button>
                      </form>
                    ) : null}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </Panel>
  );
}
