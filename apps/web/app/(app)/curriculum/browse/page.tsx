import Link from "@/components/link";
import { activities, gate, PAGE_SIZE, sections, SLOT_WORDS, SLOTS } from "@/lib/curriculum-screens";
import { Icon } from "@/lib/icons";
import { Chrome, Empty, Pager, Progress, StateChip } from "../chrome";

// The K2 curriculum by section: how much of each is filled, a section opened, its activities searched.
export default async function Browse({ searchParams }: { searchParams: Promise<Record<string, string | undefined>> }) {
  await gate();
  const q = await searchParams;
  const all = await sections();
  const section = all.some((s) => s.section === q.section) ? q.section! : "";
  const text = (q.q ?? "").trim();
  const asked = Math.max(1, Number.parseInt(q.page ?? "1", 10) || 1);
  let { rows, total } = await activities(section, text, asked);
  const last = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const page = Math.min(asked, last);
  if (page !== asked) ({ rows, total } = await activities(section, text, page)); // a page past the end shows the last
  const href = (p: number) => `/curriculum/browse?${new URLSearchParams({ ...(section ? { section } : {}), ...(text ? { q: text } : {}), page: String(p) })}`;
  return (
    <Chrome here="/curriculum/browse" title="Curriculum browser" lead="Every K2 activity by section, and how much of each page is filled in: objective, materials, steps, thinking, the four levels and the skills.">
      {all.length === 0 ? (
        <Empty>No K2 activities are loaded yet.</Empty>
      ) : (
        <div className="cs-grid">
          {all.map((s) => (
            <section key={s.section} className="cs-card cs-col-4" data-section={s.section} data-state={s.state}>
              <header>
                <h2>
                  {s.section ? <Link href={`/curriculum/browse?section=${encodeURIComponent(s.section)}`}>{s.section}</Link> : "No section named"}
                </h2>
                <StateChip state={s.state} />
              </header>
              <p className="cs-note">
                <span data-total>{s.total}</span> {s.total === 1 ? "activity" : "activities"}
              </p>
              <Progress share={s.share} state={s.state} label={`${s.section || "No section named"} filled`} />
              <dl className="cs-slots">
                {SLOTS.map((k) => (
                  <div key={k}>
                    <dt>{SLOT_WORDS[k]}</dt>
                    <dd data-slot={k}>{`${s.filled[k]} of ${s.total}`}</dd>
                  </div>
                ))}
              </dl>
            </section>
          ))}
        </div>
      )}
      <h2 style={{ marginTop: "var(--space-5)" }}>{section || "All sections"}</h2>
      <form className="cs-filter" role="search" action="/curriculum/browse">
        <div>
          <label htmlFor="q">Search by name or number</label>
          <input id="q" type="search" name="q" defaultValue={text} />
        </div>
        {section ? <input type="hidden" name="section" value={section} /> : null}
        <button className="cs-btn" type="submit">
          <Icon name="search" size={16} /> Search
        </button>
        {section || text ? <Link href="/curriculum/browse" className="cs-btn">Clear</Link> : null}
      </form>
      {rows.length === 0 ? (
        <Empty>No activity matches that.</Empty>
      ) : (
        <table className="cs-table">
          <thead>
            <tr><th>Number</th><th>Activity</th><th>Section</th><th className="n">Filled</th><th>State</th></tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.code} data-row={r.code}>
                <td><Link href={`/curriculum/fill/${r.code}`}>{r.code}</Link></td>
                <td>{r.name}</td>
                <td>{r.section}</td>
                <td className="n">{r.filled} of {SLOTS.length}</td>
                <td><StateChip state={r.state} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <Pager page={page} last={last} href={href} />
    </Chrome>
  );
}
