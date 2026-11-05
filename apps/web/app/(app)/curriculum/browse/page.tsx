import Link from "@/components/link";
import { DataTable } from "@/components/data-table";
import { FilterBar } from "@/components/filter-bar";
import { PageShell } from "@/components/page-shell";
import { requireStaff } from "@/lib/auth";
import { activities, mustBeOn, PAGE_SIZE, sections, SLOT_WORDS, SLOTS, type Row } from "@/lib/curriculum-screens";
import type { Column } from "@/lib/ux-rules";
import { Chrome, Empty, Progress, StateChip } from "../chrome";

const COLUMNS: Column<Row>[] = [
  { key: "code", label: "Number", value: (r) => r.code, cell: (r) => <Link href={`/curriculum/fill/${r.code}`}>{r.code}</Link>, width: "9rem" },
  { key: "name", label: "Activity", value: (r) => r.name },
  { key: "section", label: "Section", value: (r) => r.section, width: "10rem" },
  { key: "filled", label: "Filled", value: (r) => `${r.filled} of ${SLOTS.length}`, num: true, width: "6rem" },
  { key: "state", label: "State", value: (r) => r.state, cell: (r) => <StateChip state={r.state} />, status: true, width: "10rem" },
];

// The K2 curriculum by section: how much of each is filled, a section opened, its activities searched.
export default async function Browse({ searchParams }: { searchParams: Promise<Record<string, string | undefined>> }) {
  const me = await requireStaff();
  await mustBeOn(me.email);
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
    <PageShell
      stage="Curriculum"
      title="Curriculum browser"
      purpose="Every K2 activity by section, and how much of each page is filled in."
      action={<Link href="/curriculum/fill/walk" className="btn">Check the drafted parts</Link>}
      next={{ href: "/curriculum/fill", label: "See what is filled, and by whom" }}
    >
      <Chrome here="/curriculum/browse">
        {all.length === 0 ? (
          <Empty next={{ href: "/curriculum/fill", label: "See what is filled" }}>No K2 activities are loaded yet.</Empty>
        ) : (
          <div className="cs-grid">
            {all.map((s) => (
              <section key={s.section} className="cs-card cs-col-4" data-section={s.section} data-state={s.state}>
                <header>
                  <h2>{s.section ? <Link href={`/curriculum/browse?section=${encodeURIComponent(s.section)}`}>{s.section}</Link> : "No section named"}</h2>
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
        <h2 style={{ margin: "var(--space-5) 0 var(--space-2)" }}>{section || "All sections"}</h2>
        <FilterBar
          action="/curriculum/browse"
          filters={[{ name: "section", label: "Section", value: section, all: "Every section", options: all.filter((s) => s.section).map((s) => [s.section, s.section] as const) }]}
          search={{ name: "q", value: text, placeholder: "Search by name or number" }}
        />
        {rows.length === 0 ? (
          <Empty next={{ href: "/curriculum/browse", label: "Clear the search" }}>No activity matches that.</Empty>
        ) : (
          <DataTable label="Activities" columns={COLUMNS} rows={rows} rowKey={(r) => r.code} more={{ page, href, of: total }} extras={{ attrs: (r) => ({ "data-row": r.code }) }} />
        )}
      </Chrome>
    </PageShell>
  );
}
