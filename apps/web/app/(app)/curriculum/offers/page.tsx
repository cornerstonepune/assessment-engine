import { requireStaff } from "@/lib/auth";
import { mustBeOn, linked, PAGE_SIZE, readOffers } from "@/lib/curriculum-screens";
import { Icon } from "@/lib/icons";
import { answerOffer } from "../actions";
import { PageShell } from "@/components/page-shell";
import Link from "@/components/link";
import { Chrome, Empty, Pager } from "../chrome";

// Skills the machine offers for an activity that the examples did not show: the activity, the skills, what the school
// had already linked, and why it waits. Yes adds the link; No closes the offer.
export default async function Offers({ searchParams }: { searchParams: Promise<Record<string, string | undefined>> }) {
  const me = await requireStaff();
  const { reviews } = await mustBeOn(me.email);
  const q = await searchParams;
  const all = await readOffers(me.email);
  const last = Math.max(1, Math.ceil(all.length / PAGE_SIZE));
  const page = Math.min(last, Math.max(1, Number.parseInt(q.page ?? "1", 10) || 1));
  const shown = all.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
  const had = await linked([...new Set(shown.map((o) => o.activity.code))]);
  return (
    <PageShell
      stage="Curriculum"
      title="Skills offered, waiting for you"
      purpose={`${all.length} offered. Yes adds the skill to the activity; No closes the offer and adds nothing.`}
      action={<Link href="/curriculum/browse" className="btn">Curriculum browser</Link>}
      next={{ href: "/curriculum/fill", label: "See what is filled, and by whom" }}
    >
      <Chrome here="/curriculum/offers">
      {shown.length === 0 ? (
        <Empty next={{ href: "/curriculum/browse", label: "Back to the curriculum browser" }}>No skills are waiting for you.</Empty>
      ) : (
        <div className="cs-stack">
          {shown.map((o) => (
            <section key={o.id} className="cs-card" data-offer={o.id}>
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
              {reviews ? (
              <form action={answerOffer} className="cs-actions">
                <input type="hidden" name="id" value={o.id} />
                <button className="cs-btn" data-main type="submit" name="do" value="yes"><Icon name="confirm" size={16} /> Yes, add it</button>
                <button className="cs-btn" type="submit" name="do" value="no"><Icon name="no" size={16} /> No</button>
              </form>
              ) : null}
            </section>
          ))}
        </div>
      )}
      <Pager page={page} last={last} href={(p) => `/curriculum/offers?page=${p}`} />
      </Chrome>
    </PageShell>
  );
}
