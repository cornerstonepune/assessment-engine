import Link from "@/components/link";
import { Icon, type IconName } from "@/lib/icons";
import { gap, gate, readOffers, waiting, type State } from "@/lib/curriculum-screens";

// The breadcrumb, title and the three tabs every curriculum screen shares.
const TABS = [
  { href: "/curriculum/browse", label: "Browser" },
  { href: "/curriculum/fill", label: "What is filled" },
  { href: "/curriculum/offers", label: "Skills offered" },
] as const;

export async function Chrome({ here, crumb, title, lead, children }: { here: (typeof TABS)[number]["href"]; crumb?: string; title: string; lead: string; children: React.ReactNode }) {
  const tab = TABS.find((t) => t.href === here)!;
  const me = await gate();
  const [drafted, gaps, offered] = await Promise.all([waiting(), gap(), readOffers(me).catch(() => null)]);
  const empty = gaps.reduce((n, g) => n + g.empty, 0);
  return (
    <>
      <nav aria-label="Breadcrumb" className="cs-crumbs">
        <span>Curriculum</span>
        <span aria-hidden>›</span>
        {crumb ? <Link href={tab.href}>{tab.label}</Link> : <span aria-current="page">{tab.label}</span>}
        {crumb ? (
          <>
            <span aria-hidden>›</span>
            <span aria-current="page">{crumb}</span>
          </>
        ) : null}
      </nav>
      <h1>{title}</h1>
      <p className="cs-lead">{lead}</p>
      <nav aria-label="Counts" className="cs-strip">
        <Link href="/curriculum/fill/walk" data-count="waiting"><b>{drafted.length}</b> drafted parts to check</Link>
        <Link href="/curriculum/offers" data-count="offers"><b>{offered === null ? "–" : offered.length}</b> skills offered</Link>
        <Link href="/curriculum/fill" data-count="empty"><b>{empty}</b> parts still empty</Link>
      </nav>
      <nav aria-label="Curriculum screens" className="cs-tabs">
        {TABS.map((t) => (
          <Link key={t.href} href={t.href} aria-current={t.href === here ? "page" : undefined}>
            {t.label}
          </Link>
        ))}
      </nav>
      {children}
    </>
  );
}

export const TONE: Record<State, "done" | "soon" | "late"> = { green: "done", amber: "soon", red: "late" };
const STATE_WORDS: Record<State, [IconName, string]> = { green: ["done", "Filled"], amber: ["to-confirm", "Part filled"], red: ["fix-this", "Mostly empty"] };

/** A state is an icon, a word and a colour — never the colour alone. */
export function StateChip({ state }: { state: State }) {
  const [icon, words] = STATE_WORDS[state];
  return (
    <span className="cs-chip" data-tone={TONE[state]}>
      <Icon name={icon} size={16} /> {words}
    </span>
  );
}

export function Progress({ share, state, label }: { share: number; state: State; label: string }) {
  const pct = Math.round(share * 100);
  return (
    <div className="cs-bar" data-tone={TONE[state]} role="progressbar" aria-label={label} aria-valuemin={0} aria-valuemax={100} aria-valuenow={pct}>
      <span style={{ width: `${pct}%` }} />
    </div>
  );
}

export function Empty({ children }: { children: React.ReactNode }) {
  return (
    <div className="cs-empty" role="status">
      {children}
    </div>
  );
}
