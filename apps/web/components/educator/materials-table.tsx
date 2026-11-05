import { removeLine, setQuantity } from "@/app/(app)/educator/materials/actions";
import { Icon } from "@/lib/icons";
import type { MaterialLine } from "@/lib/educator/types";
import { E } from "@/lib/educator/words";

// One day's lines of her list as a table (D-075: rows of one kind): the item, the activity it is for (a link to its page
// comes with the activity page, M1-09a), how many (a dash when the plan gives none, never guessed; she sets it in
// place), where it is kept, remove.
const W = E.materials;
export const CELL = "border-b border-[var(--border)] px-[var(--space-2)] py-[var(--space-2)] text-left align-middle";
export const BTN = "inline-flex min-h-[var(--tap)] min-w-[var(--tap)] items-center justify-center gap-[var(--space-1)] rounded-[var(--radius-m)] border border-[var(--border-control)] bg-[var(--surface)] px-[var(--space-2)] text-[length:var(--text-label)] font-medium text-[var(--text)]";
export const FIELD = "min-h-[var(--tap)] rounded-[var(--radius-m)] border border-[var(--border-control)] bg-[var(--surface)] px-[var(--space-2)]";

const kept = (l: MaterialLine) => (!l.tracked || !l.home ? "none" : l.home);

export function MaterialsTable({ label, lines }: { label: string; lines: MaterialLine[] }) {
  return (
    <section data-group={label} aria-label={label} className="grid gap-[var(--space-2)]">
      <h2 className="text-[length:var(--text-h3)] font-semibold">{label}</h2>
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-[length:var(--text-body)]">
          <thead className="text-[length:var(--text-label)] text-[var(--text-muted)]">
            <tr>
              {[W.cols.item, W.cols.activity, W.cols.quantity, W.cols.home, W.cols.change].map((c) => (
                <th key={c} scope="col" className={`${CELL} font-medium`}>
                  {c}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {lines.map((l) => (
              <tr key={l.line_id} data-line={l.line_id}>
                <th scope="row" className={`${CELL} font-medium`}>
                  {l.item}
                </th>
                <td className={CELL}>
                  {l.activity?.name ?? null}
                </td>
                <td className={CELL}>
                  <form action={setQuantity} className="flex items-center gap-[var(--space-1)]">
                    <input type="hidden" name="line" value={l.line_id} />
                    <input name="quantity" type="number" min={0} step="any" defaultValue={l.quantity ?? ""} placeholder={W.noQty} aria-label={`${W.cols.quantity}: ${l.item}`} className={`${FIELD} w-[var(--space-7)] tabular-nums`} />
                    <span className="text-[length:var(--text-label)] text-[var(--text-muted)]">{l.unit}</span>
                    <button type="submit" className={BTN}>
                      {W.save}
                    </button>
                  </form>
                </td>
                <td className={CELL} data-home={kept(l)}>
                  {W.home[kept(l)]}
                </td>
                <td className={CELL}>
                  <form action={removeLine}>
                    <input type="hidden" name="line" value={l.line_id} />
                    <button type="submit" className={BTN} aria-label={`${W.remove}: ${l.item}`}>
                      <Icon name="clear" size={16} />
                      {W.remove}
                    </button>
                  </form>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
