import { PageShell } from "@/components/page-shell";
import { EmptyState } from "@/components/empty-state";
import { Crumbs } from "@/components/educator/crumbs";
import { CELL } from "@/components/educator/materials-table";
import { Summary } from "@/components/educator/summary";
import { requireStaff } from "@/lib/auth";
import { openTo, schoolListOf } from "@/lib/educator/data";
import { Icon } from "@/lib/icons";
import { E } from "@/lib/educator/words";
import { schoolToday } from "@/lib/voice-page";

// The school's list for a month (M1-09m, D-076): every class's list put together by the engine (M1-16), each item once
// with the classes it comes from; an item a class has not given a quantity for is marked To confirm (amber). The
// coordinator's: anyone else, and the preview, see why there is none.
const W = E.materials;

export default async function SchoolListPage({ searchParams }: { searchParams: Promise<{ month?: string }> }) {
  const me = await requireStaff();
  await openTo(me);
  const q = await searchParams;
  const month = /^\d{4}-\d{2}$/.test(q.month ?? "") ? q.month! : schoolToday().slice(0, 7);
  const from = `${month}-01`;
  const to = new Date(Date.UTC(Number(month.slice(0, 4)), Number(month.slice(5, 7)), 0)).toISOString().slice(0, 10);
  const list = await schoolListOf(me, from, to);
  const confirm = list?.lines.filter((l) => l.to_confirm) ?? [];
  return (
    <PageShell stage={E.area} title={W.schoolTitle} purpose={W.schoolPurpose} action={<span className="text-[length:var(--text-label)] text-[var(--text-muted)] tabular-nums">{month}</span>} next={{ href: "/educator/materials", label: W.classList }}>
      <Crumbs trail={[{ label: E.area }, { label: W.nav, href: "/educator/materials" }, { label: W.schoolList }]} />
      {list === null ? (
        <EmptyState>{W.notCoordinator}</EmptyState>
      ) : list.lines.length === 0 ? (
        <EmptyState>{W.schoolNone}</EmptyState>
      ) : (
        <>
          <Summary
            items={[
              { label: W.counts.items, n: list.lines.length },
              { label: W.counts.toConfirm, n: confirm.length, href: confirm[0] ? `#m-${confirm[0].material_code}` : undefined },
            ]}
          />
          <div className="overflow-x-auto">
            <table className="w-full border-collapse" data-school-list>
              <thead className="text-[length:var(--text-label)] text-[var(--text-muted)]">
                <tr>
                  {[W.cols.item, W.cols.quantity, W.fromClasses].map((c) => (
                    <th key={c} scope="col" className={`${CELL} font-medium`}>
                      {c}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {list.lines.map((l) => (
                  <tr key={l.material_code} id={`m-${l.material_code}`} data-line={l.material_code}>
                    <th scope="row" className={`${CELL} font-medium`}>
                      {l.item}
                    </th>
                    <td className={`${CELL} tabular-nums`}>
                      <span className="inline-flex flex-wrap items-center gap-[var(--space-2)]">
                        {l.quantity === null ? W.noQty : `${l.quantity} ${l.unit}`}
                        {l.to_confirm ? (
                          <span data-chip="toConfirm" className="inline-flex items-center gap-[var(--space-1)] rounded-[var(--radius-pill)] border px-[var(--space-2)] py-[var(--space-1)] text-[length:var(--text-label)] font-medium" style={{ color: "var(--needs-you-fg)", borderColor: "var(--needs-you-bd)" }}>
                            <Icon name="to-confirm" size={16} />
                            {W.toConfirm}
                          </span>
                        ) : null}
                      </span>
                    </td>
                    <td className={CELL}>{l.from.map((c) => `${c.class}${c.quantity !== null ? ` (${c.quantity})` : ""}`).join(", ")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </PageShell>
  );
}
