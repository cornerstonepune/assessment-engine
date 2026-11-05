import { gate, linked, PAGE_SIZE, readOffers } from "@/lib/curriculum-screens";
import { Icon } from "@/lib/icons";
import Link from "@/components/link";
import { answerOffer } from "../actions";
import { Chrome, Empty } from "../chrome";

// Skills the machine offers for an activity that the examples did not show: the activity, the skills, what the school
// had already linked, and why it waits. Yes adds the link; No closes the offer.
export default async function Offers({ searchParams }: { searchParams: Promise<Record<string, string | undefined>> }) {
  const me = await gate();
  const q = await searchParams;
  const all = await readOffers(me.email);
  const last = Math.max(1, Math.ceil(all.length / PAGE_SIZE));
  const page = Math.min(last, Math.max(1, Number.parseInt(q.page ?? "1", 10) || 1));
  const shown = all.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
  const had = await linked([...new Set(shown.map((o) => o.activity.code))]);
  return (
    <Chrome here="/curriculum/offers" title="Skills offered, waiting for you" lead={`${all.length} offered. Yes adds the skill to the activity; No closes the offer and adds nothing.`}>
      {shown.length === 0 ? (
        <Empty>No skills are waiting for you.</Empty>
      ) : (
        <div className="cs-grid">
          {shown.map((o) => (
            <section key={o.id} className="cs-card cs-col-8" style={{ gridColumn: "span 12" }} data-offer={o.id}>
              <header>
                <h2>{o.activity.name}</h2>
                <span className="cs-note">{o.activity.code} · {o.activity.section}</span>
              </header>
              <p className="cs-skill" data-offered>
                <b>Offered:</b> {o.skills.map((s) => `${s.code} ${s.name}`).join(", ")}
              </p>
              <p className="cs-skill" data-linked>
                <b>Already linked:</b> {(had.get(o.activity.code) ?? []).map((s) => `${s.code} ${s.name}`).join(", ") || "none"}
              </p>
              <p className="cs-note">{o.reason}</p>
              <form action={answerOffer} className="cs-actions">
                <input type="hidden" name="id" value={o.id} />
                <button className="cs-btn" data-main type="submit" name="do" value="yes"><Icon name="confirm" size={16} /> Yes, add it</button>
                <button className="cs-btn" type="submit" name="do" value="no"><Icon name="no" size={16} /> No</button>
              </form>
            </section>
          ))}
        </div>
      )}
      {last > 1 ? (
        <div className="cs-pager">
          {page > 1 ? <Link href={`/curriculum/offers?page=${page - 1}`}>Previous page</Link> : <span />}
          <span className="cs-note">Page {page} of {last}</span>
          {page < last ? <Link href={`/curriculum/offers?page=${page + 1}`}>Next page</Link> : <span />}
        </div>
      ) : null}
    </Chrome>
  );
}
