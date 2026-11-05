import Link from "@/components/link";
import { removeLine, setQuantity } from "@/app/(app)/educator/materials/actions";
import { Icon } from "@/lib/icons";
import type { Column } from "@/lib/ux-rules";
import type { MaterialLine } from "@/lib/educator/types";
import { E } from "@/lib/educator/words";

// The columns of her list, for the site's one table (DataTable, D-075: rows of one kind): the item, the activity it is
// for (a link to its page), how many (a dash when the plan gives none, never
// guessed; she sets it in place), where it is kept, remove. `look` (the staff preview): the lines only, nothing to change.
const W = E.materials;
export const BTN = "inline-flex min-h-[var(--tap)] min-w-[var(--tap)] items-center justify-center gap-[var(--space-1)] rounded-[var(--radius-m)] border border-[var(--border-control)] bg-[var(--surface)] px-[var(--space-2)] text-[length:var(--text-label)] font-medium text-[var(--text)]";
export const FIELD = "min-h-[var(--tap)] rounded-[var(--radius-m)] border border-[var(--border-control)] bg-[var(--surface)] px-[var(--space-2)]";

export type DayLine = MaterialLine & { day: string };
const kept = (l: MaterialLine) => (!l.tracked || !l.home ? "none" : l.home);
const qty = (l: MaterialLine) => (l.quantity === null ? W.noQty : `${l.quantity} ${l.unit}`);

export function materialColumns(look: boolean): Column<DayLine>[] {
  const cols: Column<DayLine>[] = [
    { key: "item", label: W.cols.item, value: (l) => l.item },
    {
      key: "activity",
      label: W.cols.activity,
      value: (l) => l.activity?.name,
      cell: (l) =>
        l.activity ? (
          <Link href={`/educator/activity/${encodeURIComponent(l.activity.code)}?back=/educator/materials`} className="inline-flex min-h-[var(--tap)] items-center text-[var(--text)] underline underline-offset-4">
            {l.activity.name}
          </Link>
        ) : null,
    },
    {
      key: "quantity",
      label: W.cols.quantity,
      value: (l) => qty(l),
      keep: true,
      cell: (l) =>
        look ? (
          <span className="tabular-nums">{qty(l)}</span>
        ) : (
          <form action={setQuantity} className="flex items-center gap-[var(--space-1)]">
            <input type="hidden" name="line" value={l.line_id} />
            <input name="quantity" type="number" min={0} step="any" defaultValue={l.quantity ?? ""} placeholder={W.noQty} aria-label={`${W.cols.quantity}: ${l.item}`} className={`${FIELD} w-[var(--space-7)] tabular-nums`} />
            <span className="text-[length:var(--text-label)] text-[var(--text-muted)]">{l.unit}</span>
            <button type="submit" className={BTN}>
              {W.save}
            </button>
          </form>
        ),
    },
    { key: "home", label: W.cols.home, value: (l) => W.home[kept(l)], cell: (l) => <span data-home={kept(l)}>{W.home[kept(l)]}</span> },
  ];
  if (look) return cols;
  return [
    ...cols,
    {
      key: "change",
      label: W.cols.change,
      value: () => W.remove,
      keep: true,
      cell: (l) => (
        <form action={removeLine}>
          <input type="hidden" name="line" value={l.line_id} />
          <button type="submit" className={BTN} aria-label={`${W.remove}: ${l.item}`}>
            <Icon name="clear" size={16} />
            {W.remove}
          </button>
        </form>
      ),
    },
  ];
}
