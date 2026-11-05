import Link from "@/components/link";
import { Crumbs } from "@/components/educator/crumbs";
import { Summary } from "@/components/educator/summary";
import { Icon, type IconName } from "@/lib/icons";
import { requireStaff } from "@/lib/auth";
import { gap, mustBeOn, readOffers, waiting, type State } from "@/lib/curriculum-screens";

// The breadcrumb and the strip of counts every curriculum screen carries (D-075), inside the page's PageShell; the menu
// down the left is the layout's (lib/curriculum-menu.ts).
const AREA = {
  "/curriculum/browse": "Curriculum",
  "/curriculum/fill": "What is filled",
  "/curriculum/offers": "Skills offered",
} as const;

/** Curriculum › where she is › the page: the browser is the area's own page, so it is named once. */
function trail(here: keyof typeof AREA, crumb?: string) {
  const area = { label: AREA[here], href: crumb ? here : undefined };
  const top = { label: "Curriculum", href: here === "/curriculum/browse" && !crumb ? undefined : "/curriculum/browse" };
  if (here === "/curriculum/browse") return crumb ? [top, { label: crumb }] : [{ label: "Curriculum" }];
  return [top, area, ...(crumb ? [{ label: crumb }] : [])];
}

export async function Chrome({ here, crumb, children }: { here: keyof typeof AREA; crumb?: string; children: React.ReactNode }) {
  const me = await requireStaff();
  const { reviews } = await mustBeOn(me.email);
  const [drafted, gaps, offered] = await Promise.all([waiting(), gap(), readOffers(me.email).catch(() => null)]);
  const empty = gaps.reduce((n, g) => n + g.empty, 0);
  return (
    <>
      <Crumbs trail={trail(here, crumb)} />
      {!reviews ? <p data-preview className="mb-[var(--space-3)] text-[length:var(--text-label)] text-[var(--text-muted)]">Preview: you can look, and change nothing, until the educator screens are switched on.</p> : null}
      <Summary
        items={[
          { label: ["drafted part to check", "drafted parts to check"], n: drafted.length, href: "/curriculum/fill/walk" },
          ...(offered ? [{ label: ["skill offered", "skills offered"] as const, n: offered.length, href: "/curriculum/offers" }] : []),
          { label: ["part still empty", "parts still empty"], n: empty, href: "/curriculum/fill" },
        ]}
      />
      {children}
    </>
  );
}

const TONE: Record<State, "done" | "soon" | "late"> = { green: "done", amber: "soon", red: "late" };
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

/** Nothing to show, said once, with where to go next (no dead ends). */
export function Empty({ children, next }: { children: React.ReactNode; next?: { href: string; label: string } }) {
  return (
    <div className="cs-empty" role="status">
      <p>{children}</p>
      {next ? (
        <p>
          <Link href={next.href}>{next.label}</Link>
        </p>
      ) : null}
    </div>
  );
}

/** Previous page, where we are, next page. `href(n)` is the address of page n. */
export function Pager({ page, last, href }: { page: number; last: number; href: (page: number) => string }) {
  if (last <= 1) return null;
  return (
    <div className="cs-pager">
      {page > 1 ? <Link href={href(page - 1)}>Previous page</Link> : <span />}
      <span className="cs-note">Page {page} of {last}</span>
      {page < last ? <Link href={href(page + 1)}>Next page</Link> : <span />}
    </div>
  );
}
