import Link from "@/components/link";
import { PageShell } from "@/components/page-shell";
import { FlowDrawing, GuideNav, MenuDrawing, Part, Rich } from "@/components/guide";
import { requireStaff } from "@/lib/auth";
import { START, guideFacts, nextAfter } from "@/lib/guide";

// Start here (goals/guide_for_educators.yaml): what the tool is for, the school's whole flow drawn from the map, the menu
// drawn from the menu, and "I want to..." buttons that land on the answer.
export default async function GuideStart() {
  await requireStaff();
  const f = await guideFacts();
  return (
    <PageShell
      stage="Guide"
      title="Start here"
      purpose={START.purpose}
      action={
        <Link href="/guide/worked-out" className="btn">
          How it is worked out
        </Link>
      }
      next={nextAfter("/guide")}
    >
      <GuideNav here="/guide" />
      <div className="grid gap-8">
        <div className="grid max-w-[720px] gap-3 text-[15.5px] leading-[1.6]">
          {START.forWhat.map((p) => (
            <p key={p}>
              <Rich p={p} f={f} />
            </p>
          ))}
        </div>
        <Part id="want" title="I want to...">
          <ul className="flex flex-wrap gap-2" data-wants>
            {START.wants.map((w) => (
              <li key={w.href}>
                <Link href={w.href} className="inline-flex min-h-11 items-center border border-terracotta/50 bg-chalk px-4 text-[14.5px] no-underline hover:bg-terracotta/10">
                  {w.label}
                </Link>
              </li>
            ))}
          </ul>
        </Part>
        <section id="flow" aria-labelledby="flow-h" className="scroll-mt-6 border-t border-basalt/12 pt-5">
          <h2 id="flow-h" className="mb-3 text-[18px]">
            The school&rsquo;s week in one picture
          </h2>
          <FlowDrawing />
        </section>
        <section id="menu" aria-labelledby="menu-h" className="scroll-mt-6 border-t border-basalt/12 pt-5">
          <h2 id="menu-h" className="mb-3 text-[18px]">
            The menu, and what each page is for
          </h2>
          <MenuDrawing />
        </section>
      </div>
    </PageShell>
  );
}
