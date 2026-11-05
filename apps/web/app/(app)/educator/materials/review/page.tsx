import { PageShell } from "@/components/page-shell";
import { EmptyState } from "@/components/empty-state";
import { Crumbs } from "@/components/educator/crumbs";
import { DataTable } from "@/components/data-table";
import { BTN, FIELD } from "@/components/educator/materials-table";
import { Summary } from "@/components/educator/summary";
import { putOnList, setAside } from "../actions";
import { requireStaff } from "@/lib/auth";
import { catalogueOf, openTo, waitingNotes } from "@/lib/educator/data";
import type { CatalogueItem, WaitingNote } from "@/lib/educator/types";
import type { Column } from "@/lib/ux-rules";
import { E } from "@/lib/educator/words";
import { schoolToday } from "@/lib/voice-page";

// The notes the system could not read for sure (M1-09m, D-076; M1-16's review routes), oldest first: a person puts what
// a note asks for on its class's list (an item from the catalogue, never free text) or sets it aside with a reason.
const W = E.materials;

const columns = (catalogue: CatalogueItem[], today: string): Column<WaitingNote>[] => [
  { key: "note", label: W.reviewTitle, value: (n) => n.text, cell: (n) => <span className="whitespace-pre-line">{n.text}</span> },
  { key: "why", label: W.why, value: (n) => n.reason },
  {
    key: "put",
    label: W.putOn,
    value: () => W.putOn,
    keep: true,
    cell: (n) => (
      <form action={putOnList} className="flex flex-wrap items-center gap-[var(--space-1)]">
        <input type="hidden" name="note" value={n.id} />
        <select name="code" required aria-label={W.add} defaultValue="" className={FIELD}>
          <option value="">{W.add}</option>
          {catalogue.map((c) => (
            <option key={c.code} value={c.code}>
              {c.name}
            </option>
          ))}
        </select>
        <input name="quantity" type="number" min={0} step="any" defaultValue={1} aria-label={W.cols.quantity} className={`${FIELD} w-[var(--space-7)]`} />
        <input name="day" type="date" defaultValue={today} aria-label={W.neededOn} className={FIELD} />
        <button type="submit" className={BTN}>
          {W.putOn}
        </button>
      </form>
    ),
  },
  {
    key: "aside",
    label: W.setAside,
    value: () => W.setAside,
    keep: true,
    cell: (n) => (
      <form action={setAside} className="flex flex-wrap items-center gap-[var(--space-1)]">
        <input type="hidden" name="note" value={n.id} />
        <input name="why" required aria-label={W.setAsideWhy} placeholder={W.setAsideWhy} className={FIELD} />
        <button type="submit" className={BTN}>
          {W.setAside}
        </button>
      </form>
    ),
  },
];

export default async function ReviewPage({ searchParams }: { searchParams: Promise<{ page?: string }> }) {
  const me = await requireStaff();
  await openTo(me);
  const [notes, catalogue] = await Promise.all([waitingNotes(me), catalogueOf(me)]);
  const today = schoolToday();
  const q = await searchParams;
  return (
    <PageShell stage={E.area} title={W.reviewTitle} purpose={W.reviewPurpose} action={<span />} next={{ href: "/educator/materials", label: W.classList }}>
      <Crumbs trail={[{ label: E.area }, { label: W.nav, href: "/educator/materials" }, { label: W.review }]} />
      {notes === null ? (
        <EmptyState>{W.notReviewer}</EmptyState>
      ) : notes.length === 0 ? (
        <EmptyState>{W.reviewNone}</EmptyState>
      ) : (
        <>
          <Summary items={[{ label: W.counts.notes, n: notes.length, href: `#n-${notes[0].id}` }]} />
          <DataTable
            label={W.reviewTitle}
            columns={columns(catalogue, today)}
            rows={notes}
            rowKey={(n) => n.id}
            more={{ page: Number(q.page) || 1, href: (n: number) => `/educator/materials/review?page=${n}` }}
            extras={{ attrs: (n) => ({ "data-note": n.id, id: `n-${n.id}` }) }}
          />
        </>
      )}
    </PageShell>
  );
}
