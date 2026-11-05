import Link from "@/components/link";
import { requireStaff } from "@/lib/auth";
import { mustBeOn, readPage, waiting } from "@/lib/curriculum-screens";
import { PageShell } from "@/components/page-shell";
import { Chrome, Empty } from "../../chrome";
import { PartCard } from "../../parts";

// The drafted parts, one at a time: the one a checker doubted first. Answering one takes it out of the line, so the next
// one is always the first; "Skip" moves along it without answering.
export default async function Walk({ searchParams }: { searchParams: Promise<Record<string, string | undefined>> }) {
  const me = await requireStaff();
  const { reviews } = await mustBeOn(me.email);
  const q = await searchParams;
  const part = q.part ?? "";
  const line = (await waiting()).filter((w) => !part || w.part === part);
  const skip = Math.min(Math.max(0, Number.parseInt(q.skip ?? "0", 10) || 0), Math.max(0, line.length - 1));
  const here = new URLSearchParams({ ...(part ? { part } : {}), ...(skip ? { skip: String(skip) } : {}) });
  const back = `/curriculum/fill/walk${here.size ? `?${here}` : ""}`;
  const item = line[skip];
  const page = item ? await readPage(me, item.code) : null;
  const card = page?.parts.find((p) => p.part === item?.part);
  return (
    <PageShell
      stage="Curriculum"
      title="Check the drafted parts"
      purpose="Read each draft. Keep it, change it, or send it back to be empty again."
      action={<Link href="/curriculum/fill" className="btn">Back to what is filled</Link>}
      next={{ href: "/curriculum/offers", label: "See the skills offered" }}
    >
      <Chrome here="/curriculum/fill" crumb="Check the drafted parts">
        {!item || !page || !card ? (
          <Empty next={{ href: "/curriculum/fill", label: "Back to what is filled" }}>Nothing is waiting for a check.</Empty>
        ) : (
          <div data-walk>
            <p className="cs-note">
              {skip + 1} of {line.length} waiting for a check · {page.section} · <Link href={`/curriculum/fill/${page.code}`}>{page.code}</Link> {page.name}
            </p>
            <PartCard part={card} code={page.code} back={back} editing={q.edit === "1"} editHref={`${back}${here.size ? "&" : "?"}edit=1`} readOnly={!reviews} />
            {line.length > 1 ? (
              <div className="cs-pager">
                <span />
                <Link href={`/curriculum/fill/walk?${new URLSearchParams({ ...(part ? { part } : {}), skip: String((skip + 1) % line.length) })}`}>Skip for now</Link>
              </div>
            ) : null}
          </div>
        )}
      </Chrome>
    </PageShell>
  );
}
