import Link from "@/components/link";
import { ChildStateChip } from "@/components/child-state-chip";
import { DataTable } from "@/components/data-table";
import { Crumbs } from "@/components/educator/crumbs";
import { PageShell } from "@/components/page-shell";
import { Notice } from "../notice";
import { requireStaff } from "@/lib/auth";
import { Icon } from "@/lib/icons";
import { seenCounts, type Cell, type ClassPicture } from "@/lib/k2-child";
import type { Column } from "@/lib/ux-rules";
import { classPicture } from "@/lib/k2-reads";

// The class picture (task M1-17): the class's children by Sr. No. against the skills anyone was seen on. A cell exists
// only where a child was seen; an empty cell is "not seen", which is not "not secure" (D-008). Staff only: no parent route.
export default async function TheClassPicture({ params, searchParams }: { params: Promise<{ class: string }>; searchParams: Promise<{ page?: string }> }) {
  const me = await requireStaff();
  const { class: classId } = await params;
  const page = Number((await searchParams).page) || 1;
  const got = await classPicture(me.email, classId);
  return (
    <PageShell
      stage="Children"
      title={got.ok ? `Class picture · ${got.value.class}` : "Class picture"}
      purpose="Who has been seen on which skill, and where each child is. An empty square means not seen yet, nothing more."
      action={<Link href={`/voice/form?class=${classId}`} className="btn secondary inline-flex items-center gap-1.5"><Icon name="form" />Fill the form</Link>}
      next={{ href: "/today", label: "Back to what needs doing" }}
    >
      <Crumbs trail={[{ label: "Children", href: "/k2" }, { label: got.ok ? got.value.class : "Class picture" }]} />
      {got.ok ? <Picture p={got.value} classId={classId} page={page} /> : <Notice flush>{got.message}</Notice>}
    </PageShell>
  );
}

function Picture({ p, classId, page }: { p: ClassPicture; classId: string; page: number }) {
  if (p.skills.length === 0) {
    return <Notice flush>No child in this class has been seen on a skill yet. Confirmed notes and forms appear here.</Notice>;
  }
  const states = new Map<string, { cell: Cell; n: number }>();
  for (const c of p.children) for (const cell of Object.values(c.cells)) states.set(cell.state, { cell, n: (states.get(cell.state)?.n ?? 0) + 1 });
  return (
    <>
      <ul className="mb-4 flex flex-wrap gap-2" aria-label="Skills by state, all children" data-k2="strip">
        {[...states].sort().map(([code, { cell, n }]) => (
          <li key={code}><ChildStateChip state={code} words={cell.words} colour={cell.colour} />{" "}<span className="text-[13px]">{n}</span></li>
        ))}
      </ul>
      <div data-k2="grid">
        <DataTable<Row>
          label="Children by Sr. No. against skills. A dash means not seen yet."
          columns={columns(p, classId)}
          rows={p.children}
          rowKey={(r) => r.roll_no}
          more={{ page, href: (n: number) => `/k2/${classId}?page=${n}` }}
        />
      </div>
    </>
  );
}

type Row = ClassPicture["children"][number];

// One column for the child's Sr. No. and one for each skill anyone was seen on. A cell is a chip where the child was seen,
// and a dash where not: "not seen yet", which is not "not secure". Links are basalt: terracotta is never on a child.
function columns(p: ClassPicture, classId: string): Column<Row>[] {
  const seen = seenCounts(p);
  const to = (r: Row) => `/k2/${classId}/${encodeURIComponent(r.roll_no)}`;
  return [
    { key: "roll", label: "Sr. No.", keep: true, value: (r) => r.roll_no, cell: (r) => <Link href={to(r)} className="text-[var(--text)] underline">{r.roll_no}</Link> },
    ...p.skills.map((s): Column<Row> => ({
      key: s.code,
      label: `${s.name} · ${seen[s.code]} seen`,
      status: true,
      value: (r) => r.cells[s.code]?.state,
      cell: (r) => {
        const c = r.cells[s.code];
        return c ? (
          <Link href={to(r)} className="text-[var(--text)]" aria-label={`Sr. No. ${r.roll_no}, ${s.name}: ${c.words}${c.level === null ? "" : `, level ${c.level}`}`}>
            <ChildStateChip state={c.state} words={c.words} colour={c.colour} level={c.level} compact />
          </Link>
        ) : (
          <span data-seen="no" aria-label={`Sr. No. ${r.roll_no}, ${s.name}: not seen yet`}>–</span>
        );
      },
    })),
  ];
}
