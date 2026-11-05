import Link from "@/components/link";
import { PageShell } from "@/components/page-shell";
import { requireStaff } from "@/lib/auth";
import { EngineDown } from "@/lib/engine";
import { type Block, type Edit, type Fixed, type Limit, type Rules, blockWhen, day, DAYS, rulesOf, standing } from "@/lib/timetable-rules";
import { changeRule } from "./actions";
import "@/design-system/tokens.css";
import "../timetable.css";

type Props = { searchParams: Promise<Record<string, string | undefined>> };

const name = (code: string) => code.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase());
const when = (iso: string) => new Date(iso).toLocaleString("en-IN", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit", timeZone: "Asia/Kolkata" });

function said(e: Edit): string {
  const a = (e.after ?? e.before ?? {}) as Record<string, unknown>;
  const verb = e.action === "remove" ? "removed" : e.before ? "changed" : "added";
  const what = { period: `period ${a.label ?? ""}`, block: `a block (${a.reason ?? ""})`, limit: `a limit on ${name(String(a.subject_code ?? ""))}`, fixed: `a fixed slot (${a.text ?? ""})` }[e.rule];
  return `${e.who} ${verb} ${what}`;
}

function Hidden({ rule, rules, action = "set", id }: { rule: string; rules: Rules; action?: string; id?: string }) {
  return (
    <>
      <input type="hidden" name="class_id" value={rules.class.id} />
      <input type="hidden" name="rule" value={rule} />
      <input type="hidden" name="action" value={action} />
      {id ? <input type="hidden" name="id" value={id} /> : null}
    </>
  );
}

const Remove = ({ rule, rules, id, word }: { rule: string; rules: Rules; id: string; word: string }) => (
  <form action={changeRule}>
    <Hidden rule={rule} rules={rules} action="remove" id={id} />
    <button className="quiet">{word}</button>
  </form>
);

function Periods({ rules }: { rules: Rules }) {
  return (
    <section className="tt-card" aria-labelledby="h-periods">
      <h2 id="h-periods">Period times</h2>
      <p className="tt-note">When each period starts and ends (the last may have no end). A period belongs to the grade: a change is for every class of it.</p>
      {rules.periods.map((p) => (
        <form key={p.id} action={changeRule} className="tt-row" aria-label={`Period ${p.label}`}>
          <Hidden rule="period" rules={rules} id={p.id} />
          <label>Name<input name="label" defaultValue={p.label} required /></label>
          <label>Starts<input type="time" name="starts_at" defaultValue={p.starts_at} required /></label>
          <label>Ends<input type="time" name="ends_at" defaultValue={p.ends_at ?? ""} /></label>
          <button>Save</button>
        </form>
      ))}
    </section>
  );
}

function Blocks({ rules }: { rules: Rules }) {
  return (
    <section className="tt-card" id="block" aria-labelledby="h-block">
      <h2 id="h-block">Blocked days and periods</h2>
      <p className="tt-note">Nothing is placed on a blocked day or period. Give one date, or a weekday of every week.</p>
      {rules.blocks.length === 0 ? (
        <p className="tt-empty">Nothing is blocked. Block a day when school is off, or a period that must stay free.</p>
      ) : (
        <ul className="tt-list">
          {rules.blocks.map((b: Block) => (
            <li key={b.id}>
              <span className="tt-chip late">Blocked</span>
              <span className="grow"><strong>{blockWhen(b)}</strong>, {b.period ?? "the whole day"}. {b.reason}</span>
              <Remove rule="block" rules={rules} id={b.id} word="Remove" />
            </li>
          ))}
        </ul>
      )}
      <form action={changeRule} className="tt-row">
        <Hidden rule="block" rules={rules} />
        <label>Date<input type="date" name="on_date" /></label>
        <label>Or weekday
          <select name="weekday" defaultValue=""><option value="">None</option>{DAYS.slice(1).map((d, i) => <option key={d} value={i + 1}>{d}</option>)}</select>
        </label>
        <label>Week
          <select name="week_code" defaultValue=""><option value="">Both</option><option value="A">A</option><option value="B">B</option></select>
        </label>
        <label>Period
          <select name="period_id" defaultValue=""><option value="">Whole day</option>{rules.periods.map((p) => <option key={p.id} value={p.id}>{p.starts_at} {p.label}</option>)}</select>
        </label>
        <label>Reason<input name="reason" required /></label>
        <button>Block</button>
      </form>
    </section>
  );
}

function Limits({ rules }: { rules: Rules }) {
  return (
    <section className="tt-card" aria-labelledby="h-limits">
      <h2 id="h-limits">Fewest and most periods of a subject</h2>
      <p className="tt-note">Per week or per fortnight. Saving a subject and span again replaces its limit.</p>
      {rules.limits.length === 0 ? (
        <p className="tt-empty">No limits yet. Set the most periods of a subject, the fewest, or both.</p>
      ) : (
        <ul className="tt-list">
          {rules.limits.map((l: Limit) => {
            const s = standing(l, rules.placed);
            return (
              <li key={l.id}>
                <span className="grow"><strong>{name(l.subject_code)}</strong>, per {l.span}: {l.fewest ?? "no"} fewest, {l.most ?? "no"} most</span>
                <span className={`tt-chip ${s.state === "within" ? "done" : "soon"}`}>
                  {s.state === "within" ? `${s.now} placed, within` : s.state === "over" ? `${s.now} placed, over` : `${s.now} placed, under`}
                </span>
                <Remove rule="limit" rules={rules} id={l.id} word="Remove" />
              </li>
            );
          })}
        </ul>
      )}
      <form action={changeRule} className="tt-row">
        <Hidden rule="limit" rules={rules} />
        <label>Subject<select name="subject_code" required>{rules.subjects.map((s) => <option key={s.code} value={s.code}>{s.name}</option>)}</select></label>
        <label>Per<select name="span"><option value="week">Week</option><option value="fortnight">Fortnight</option></select></label>
        <label>Fewest<input type="number" name="fewest" min={0} /></label>
        <label>Most<input type="number" name="most" min={0} /></label>
        <button>Save limit</button>
      </form>
    </section>
  );
}

function FixedSlots({ rules }: { rules: Rules }) {
  return (
    <section className="tt-card" aria-labelledby="h-fixed">
      <h2 id="h-fixed">Fixed slots</h2>
      <p className="tt-note">Pinned by the school: this period, this weekday, this week. Pinning over a lesson replaces it and keeps it in the changes.</p>
      {rules.fixed.length === 0 ? (
        <p className="tt-empty">No slot is fixed yet.</p>
      ) : (
        ["A", "B"].flatMap((w) => [1, 2, 3, 4, 5].map((d) => ({ w, d, rows: rules.fixed.filter((f: Fixed) => f.week === w && f.weekday === d) })))
          .filter((g) => g.rows.length > 0)
          .map((g) => (
            <details key={`${g.w}${g.d}`} open={g.w === "A" && g.d === 1}>
              <summary><strong>Week {g.w}, {day(g.d)}</strong> <span className="tt-note">{g.rows.length} fixed</span></summary>
              <ul className="tt-list">
                {g.rows.map((f: Fixed) => (
                  <li key={f.id}>
                    <span className="grow">{f.label}: <span className="tt-school">{f.text}</span></span>
                    <Remove rule="fixed" rules={rules} id={f.id} word="Release" />
                  </li>
                ))}
              </ul>
            </details>
          ))
      )}
      <form action={changeRule} className="tt-row">
        <Hidden rule="fixed" rules={rules} />
        <label>Week<select name="week_code"><option>A</option><option>B</option></select></label>
        <label>Weekday<select name="weekday">{DAYS.slice(1).map((d, i) => <option key={d} value={i + 1}>{d}</option>)}</select></label>
        <label>Period<select name="period_id">{rules.periods.map((p) => <option key={p.id} value={p.id}>{p.starts_at} {p.label}</option>)}</select></label>
        <label>What is fixed<input name="text" required /></label>
        <button>Pin</button>
      </form>
    </section>
  );
}

export default async function RulesPage({ searchParams }: Props) {
  const me = await requireStaff();
  const q = await searchParams;
  let rules: Rules | null = null;
  let down: string | null = null;
  try {
    rules = await rulesOf(me.email, q.class || undefined);
  } catch (e) {
    if (!(e instanceof EngineDown)) throw e;
    down = e.message;
  }
  return (
    <PageShell
      stage="Timetable"
      title="Timetable rules"
      purpose="Period times, blocked days, fixed slots and subject limits, kept as rows with who changed them."
      action={<a href="#block" className="btn">Block a day</a>}
      next={{ href: "/today", label: "What needs doing" }}
    >
      <div className="tt">
        {down ? <p className="tt-chip late" role="alert">{down}</p> : null}
        {q.error ? <p className="tt-chip late" role="alert">{q.error}</p> : null}
        {q.saved ? <p className="tt-chip done" role="status">Saved.</p> : null}
        {rules === null ? (
          !down && <p className="tt-empty">No class has a timetable yet. Rules appear here once the school&apos;s timetable is loaded.</p>
        ) : (
          <>
            <nav aria-label="Class" className="tt-note">
              Class{" "}
              {rules.classes.map((c) => (
                <Link key={c.id} href={`/timetable/rules?class=${c.id}`} className="chip" aria-current={c.id === rules.class.id ? "page" : undefined}>
                  {c.grade} {c.section}
                </Link>
              ))}
            </nav>
            <div className="tt-grid">
              <Blocks rules={rules} />
              <Limits rules={rules} />
              <FixedSlots rules={rules} />
              <Periods rules={rules} />
              <section className="tt-card" aria-labelledby="h-hist">
                <h2 id="h-hist">Changes</h2>
                {rules.history.length === 0 ? (
                  <p className="tt-empty">No rule has been changed yet.</p>
                ) : (
                  <ul className="tt-list">
                    {rules.history.slice(0, 8).map((e) => (
                      <li key={e.id}><span className="tt-note">{when(e.at)}</span><span className="grow">{said(e)}</span></li>
                    ))}
                  </ul>
                )}
              </section>
            </div>
          </>
        )}
      </div>
    </PageShell>
  );
}
