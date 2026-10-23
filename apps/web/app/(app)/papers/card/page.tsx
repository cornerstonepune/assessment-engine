import Link from "@/components/link";
import { DataTable } from "@/components/data-table";
import { FilterBar } from "@/components/filter-bar";
import { StatusChip } from "@/components/status-chip";
import { PageShell } from "@/components/page-shell";
import { Notice, Panel } from "@/components/shell";
import { requireStaff } from "@/lib/auth";
import { deadline } from "@/lib/deadline";
import { classWords } from "@/lib/needs-you";
import { grades } from "@/lib/queries";
import { assessmentCard, CARD_STAGES, type Card, type CardCopy, type CardKey, standing } from "@/lib/queries-card";
import { KIND_WORDS, STAGE_WORDS } from "@/lib/queries-papers";
import type { Column } from "@/lib/ux-rules";
import { dateWords, weekWords } from "@/lib/week";
import { UploadScans } from "../../capture/upload-scans";
import { STAGE_STATE } from "../copies-table";
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
  // the school's day, as the engine checks it: "2026-10-22" in Pune, whatever the server's clock
  const today = new Date().toLocaleDateString("en-CA", { timeZone: "Asia/Kolkata" });
  return (
    <PageShell
      stage="Assessments · its card"
      title={key.kind === "focus" ? "Home assessments" : title}
      purpose={`${KIND_WORDS[key.kind] ?? key.kind} · ${band ? classWords(g, band, key.class) : key.class} · ${weekWords(key.week || null)}`}
      action={s.n === 0 ? <Link className="btn" href="/papers">Open Assessments →</Link> : <MainAction card={card} s={s} today={today} />}
      next={s.n === 0 ? { href: "/", label: "Today" } : { href: "/papers", label: "All assessments" }}
    >
      {q.said ? <Notice tone="terracotta">{q.said}</Notice> : null}
      {s.n === 0 ? (
        <p className="note">No paper of this class, week and kind was found: open it from Assessments.</p>
      ) : (
        <div className="grid min-w-0 gap-[18px]">
          <div id="papers-in">
            <Panel title="Papers in" label="Papers in" aside={`${s.inn} of ${s.n} in`}>
              <UploadScans reading={!!card.reading} />
              <p className="mt-2 text-[13px] text-basalt/70">
                Put in the scan or the photos of any papers: each page goes where its printed code says, whichever card you put it in from.
              </p>
            </Panel>
          </div>
          <Stages at={s.at} done={s.done} />
          <Next card={card} s={s} />
          <Copies card={card} page={Number(q.page) || 1} where={q.where} />
        </div>
      )}
    </PageShell>
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
        <p className="text-[13.5px]">The system proposed each child&apos;s paper; change any child before it prints.</p>
      ) : null}
      {s.at === "Given" ? <p className="text-[13.5px]">Say the day it was given, at the top.</p> : null}
      {s.at === "Papers in" || s.at === "Read" ? <p className="text-[13.5px]">Put the papers in at the top of this card. A child who was away is marked below; their paper is held for later, not missing.</p> : null}
      {s.at === "Checked" ? <p className="text-[13.5px]">Some answers wait for a person: check them, then sign off.</p> : null}
      {s.at === "Signed off" ? <p className="text-[13.5px]">Checked: sign each child off, then the results show here.</p> : null}
      {s.at === "Results" ? <p className="text-[13.5px]">Every paper is signed off: each child&apos;s score is below, and each child opens their profile.</p> : null}
    </Panel>
  );
}

/** The one thing to do at this stage, at the top of the page. */
function MainAction({ card, s, today }: { card: Card; s: Standing; today: string }) {
  const { key } = card;
  if (s.at === "Made" || s.at === "Approved for print")
    return (
      <Link className="btn" href={key.kind === "focus" ? `/make/${encodeURIComponent(key.class)}` : `/papers/approve?section=${encodeURIComponent(key.class)}&week=${encodeURIComponent(key.week)}&kind=${key.kind}`}>
        Look over and approve for print →
      </Link>
    );
  if (s.at === "Given")
    return (
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
    );
  if (s.at === "Checked")
    return (
      <Link className="btn" href="/capture/check">
        Check them →
      </Link>
    );
  if (s.at === "Signed off")
    return (
      <Link className="btn" href={`/capture?by=child&class=${encodeURIComponent(key.class)}`}>
        Sign them off →
      </Link>
    );
  if (s.at === "Results")
    return (
      <Link className="btn" href="/growth">
        See the class results →
      </Link>
    );
  return (
    <Link className="btn" href="#papers-in">
      Put the papers in ↓
    </Link>
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

const away_ = (c: CardCopy) => ["made", "printed"].includes(c.stage) && c.printed;

/** Each child's paper, those still out first (rule 3 of docs/ux-rules.md: ten to a page, the rest a page away). */
function Copies({ card, page, where }: { card: Card; page: number; where?: string }) {
  const out = (c: CardCopy) => ["made", "printed"].includes(c.stage);
  const stages = [...new Set(card.copies.map((c) => c.stage))];
  const at = stages.find((x) => x === where);
  const all = [...card.copies.filter(out), ...card.copies.filter((c) => !out(c))];
  const rows = at ? all.filter((c) => c.stage === at) : all;
  const columns: Column<CardCopy>[] = [
    { key: "roll", label: "Roll", value: (c) => c.roll_no },
    {
      key: "child",
      label: "Child",
      value: (c) => c.child,
      cell: (c) => (c.child_id ? <Link href={`/growth/${c.child_id}`}>{c.child ?? "this child"}</Link> : "spare"),
    },
    {
      key: "paper",
      label: "Paper",
      value: (c) => c.title,
      cell: (c) => (
        <>
          {c.title}
          <span className="block text-[11.5px] text-basalt/55">
            code <Link href={`/worksheets/${c.qr}`}>{c.qr}</Link>
          </span>
        </>
      ),
    },
    {
      key: "where",
      label: "Where it is",
      status: true,
      value: (c) => (c.away && out(c) ? "away · held for later" : STAGE_WORDS[c.stage]),
      cell: (c) => <StatusChip state={STAGE_STATE[c.stage]} words={c.away && out(c) ? "away · held for later" : STAGE_WORDS[c.stage]} />,
    },
    { key: "score", label: "Score", num: true, value: (c) => (c.scored ? `${c.right} of ${c.scored}` : null) },
    {
      key: "away",
      label: "Away",
      value: (c) => (away_(c) ? "away" : null),
      cell: (c) =>
        away_(c) ? (
          <form action={away}>
            <Back k={card.key} />
            <input type="hidden" name="qr" value={c.qr} />
            <input type="hidden" name="away" value={c.away ? "no" : "yes"} />
            <button type="submit" className="btn secondary whitespace-nowrap text-[12.5px]">
              {c.away ? "Back: count as missing" : "Away: hold it for later"}
            </button>
          </form>
        ) : null,
    },
  ];
  const { class: cls, week, kind, set } = card.key;
  const to = (p: number) => `/papers/card?${new URLSearchParams({ class: cls, week, kind, ...(set ? { set } : {}), ...(at ? { where: at } : {}), page: String(p) })}`;
  return (
    <Panel title="Each child's paper" label="Each child's paper">
      <FilterBar
        action="/papers/card"
        keep={{ class: cls, week, kind, set }}
        filters={[{ name: "where", label: "Where it is", value: at, all: "Anywhere", options: stages.map((x) => [x, STAGE_WORDS[x]] as const) }]}
      />
      <DataTable label="Each child's paper" columns={columns} rows={rows} rowKey={(c) => c.qr} more={{ page, href: to }} />
    </Panel>
  );
}
