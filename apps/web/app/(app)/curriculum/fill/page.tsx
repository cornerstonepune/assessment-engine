import Link from "@/components/link";
import { DataTable } from "@/components/data-table";
import { FilterBar } from "@/components/filter-bar";
import { PageShell } from "@/components/page-shell";
import { requireStaff } from "@/lib/auth";
import { type Gap, gap, mustBeOn, SLOT_WORDS, waiting } from "@/lib/curriculum-screens";
import { PART_KEYS } from "@/lib/page-part";
import type { Column } from "@/lib/ux-rules";
import { Chrome, Empty } from "../chrome";

const count = (k: "school" | "drafted" | "person" | "empty", label: string): Column<Gap> => ({
  key: k,
  label,
  value: (r) => r[k],
  cell: (r) => (k === "drafted" && r.drafted > 0 ? <Link href={`/curriculum/fill/walk?part=${r.part}`}>{r.drafted}</Link> : r[k]),
  num: true,
  keep: true,
});
const COLUMNS: Column<Gap>[] = [
  { key: "part", label: "Part", value: (r) => SLOT_WORDS[r.part], width: "14rem" },
  count("school", "The school's"),
  count("drafted", "Drafted, check me"),
  count("person", "Kept by a person"),
  count("empty", "Empty"),
];

// Per part of the page: how many K2 activities hold the school's words, a draft waiting for a check, a person's
// words, or nothing. A person can walk the drafted ones one by one.
export default async function Fill({ searchParams }: { searchParams: Promise<Record<string, string | undefined>> }) {
  const me = await requireStaff();
  await mustBeOn(me.email);
  const q = await searchParams;
  const [all, queue] = await Promise.all([gap(), waiting()]);
  const part = (PART_KEYS as readonly string[]).includes(q.part ?? "") ? q.part! : "";
  const rows = all.filter((r) => !part || r.part === part);
  const total = all[0] ? all[0].school + all[0].drafted + all[0].person + all[0].empty : 0;
  return (
    <PageShell
      stage="Curriculum"
      title="What is filled, and by whom"
      purpose={`For each part of the ${total} K2 activities: the school's words, a draft to check, a person's words, or empty.`}
      action={queue.length ? <Link href="/curriculum/fill/walk" className="btn">Check the drafted parts ({queue.length})</Link> : <Link href="/curriculum/browse" className="btn">Curriculum browser</Link>}
      next={{ href: "/curriculum/offers", label: "See the skills offered" }}
    >
      <Chrome here="/curriculum/fill">
        {queue.length === 0 ? <Empty next={{ href: "/curriculum/offers", label: "See the skills offered" }}>Nothing is waiting for a check.</Empty> : null}
        <FilterBar action="/curriculum/fill" filters={[{ name: "part", label: "Part", value: part, all: "Every part", options: PART_KEYS.map((p) => [p, SLOT_WORDS[p]] as const) }]} />
        <DataTable label="Parts of a page" columns={COLUMNS} rows={rows} rowKey={(r) => r.part} more={{ page: 1, href: () => "/curriculum/fill" }} extras={{ attrs: (r) => ({ "data-part": r.part }) }} />
      </Chrome>
    </PageShell>
  );
}
