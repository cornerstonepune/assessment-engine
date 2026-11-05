import { edit, keep, sendBack } from "@/app/(app)/educator/activity/[code]/actions";
import { Icon } from "@/lib/icons";
import type { PagePart } from "@/lib/page-part";
import { E } from "@/lib/educator/words";

// Her answers to a drafted part on the educator's activity page (M1-09a), given to the shared PartView as its `actions`:
// Keep it, Send it back, or Edit it in place (the steps one a line; how to think as an idea and slips). Any member of
// staff may answer, as M1-12b's routes allow; the school's own words never get these.
const W = E.page;
const BTN = "inline-flex min-h-[var(--tap)] items-center gap-[var(--space-1)] rounded-[var(--radius-m)] border border-[var(--border-control)] bg-[var(--surface)] px-[var(--space-3)] text-[length:var(--text-label)] font-medium text-[var(--text)]";
const FIELD = "w-full rounded-[var(--radius-m)] border border-[var(--border-control)] bg-[var(--surface)] p-[var(--space-2)] text-[length:var(--text-body)]";

export function Answers({ code, p }: { code: string; p: PagePart }) {
  const hidden = (
    <>
      <input type="hidden" name="code" value={code} />
      <input type="hidden" name="part" value={p.part} />
      <input type="hidden" name="kind" value={p.kind} />
    </>
  );
  return (
    <div className="mt-[var(--space-2)] grid gap-[var(--space-2)]" data-answers>
      <div className="flex flex-wrap gap-[var(--space-2)]">
        <form action={keep}>
          {hidden}
          <button type="submit" className={BTN}>
            <Icon name="confirm" size={16} />
            {W.keep}
          </button>
        </form>
        <form action={sendBack}>
          {hidden}
          <button type="submit" className={BTN}>
            <Icon name="send-back" size={16} />
            {W.sendBack}
          </button>
        </form>
      </div>
      <details className="grid gap-[var(--space-2)]">
        <summary className={`${BTN} w-fit cursor-pointer list-none`}>
          <Icon name="correct" size={16} />
          {W.edit}
        </summary>
        <form action={edit} className="mt-[var(--space-2)] grid gap-[var(--space-2)]">
          {hidden}
          {p.kind === "bullets" ? (
            <label className="grid gap-[var(--space-1)]">
              <span className="text-[length:var(--text-label)] text-[var(--text-muted)]">{W.itemsHint}</span>
              <textarea name="items" rows={Math.max(4, p.items.length + 1)} defaultValue={p.items.join("\n")} className={FIELD} />
            </label>
          ) : p.kind === "thinking" ? (
            <>
              <label className="grid gap-[var(--space-1)]">
                <span className="text-[length:var(--text-label)] text-[var(--text-muted)]">{W.idea}</span>
                <input name="idea" defaultValue={p.idea ?? ""} className={FIELD} />
              </label>
              <label className="grid gap-[var(--space-1)]">
                <span className="text-[length:var(--text-label)] text-[var(--text-muted)]">{W.slipsHint}</span>
                <textarea name="slips" rows={4} defaultValue={p.slips.map((s) => `${s.keyword}: ${s.spot}`).join("\n")} className={FIELD} />
              </label>
            </>
          ) : (
            <label className="grid gap-[var(--space-1)]">
              <span className="sr-only">{p.part}</span>
              <textarea name="text" rows={4} defaultValue={p.text} className={FIELD} />
            </label>
          )}
          <button type="submit" className={`${BTN} w-fit`}>
            {W.save}
          </button>
        </form>
      </details>
    </div>
  );
}
