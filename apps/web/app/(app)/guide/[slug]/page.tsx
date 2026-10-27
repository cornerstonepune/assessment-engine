import { notFound } from "next/navigation";
import type { ReactNode } from "react";
import Link from "@/components/link";
import { PageShell } from "@/components/page-shell";
import { Swatch } from "@/components/colour-key";
import { GuideNav, LadderDrawing, PageDrawing, Part, Rich } from "@/components/guide";
import { requireStaff } from "@/lib/auth";
import { ARTICLES, MENU_GUIDE, guideFacts, nextAfter } from "@/lib/guide";
import { childStates } from "@/lib/states";

// A page of the Guide (goals/guide_for_educators.yaml): one for each menu item, in the menu's order, or one of the guide's
// own (How it is worked out; Words and surprises; Report a problem). Its words are apps/web/guide/*.json.
export default async function GuidePage({ params }: { params: Promise<{ slug: string }> }) {
  await requireStaff();
  const { slug } = await params;
  const f = await guideFacts();
  const here = `/guide/${slug}`;
  const menu = MENU_GUIDE.find((m) => m.slug === slug);
  if (menu) {
    const g = menu.guide;
    return (
      <PageShell
        stage={`Guide · ${menu.group}`}
        title={menu.page.label}
        purpose={`What ${menu.page.label} is for, what you see where, the usual jobs, and what each button does.`}
        action={
          <Link href={menu.page.href} className="btn">
            Open {menu.page.label}
          </Link>
        }
        next={nextAfter(here)}
      >
        <GuideNav here={here} />
        <div className="grid gap-8">
          <Part id="for" title="What it is for">
            {g.forWhat.map((p) => (
              <p key={p}>
                <Rich p={p} f={f} />
              </p>
            ))}
          </Part>
          <section id="layout" aria-labelledby="layout-h" className="scroll-mt-6 border-t border-basalt/12 pt-5">
            <h2 id="layout-h" className="mb-3 text-[18px]">
              What you see where
            </h2>
            <PageDrawing title={menu.page.label} layout={g.layout} f={f} />
          </section>
          {g.jobs.map((j) => (
            <Part key={j.id} id={j.id} title={j.title}>
              <ol className="grid list-decimal gap-2 pl-6">
                {j.steps.map((s) => (
                  <li key={s}>
                    <Rich p={s} f={f} />
                  </li>
                ))}
              </ol>
            </Part>
          ))}
          <Part id="buttons" title="What each button does">
            <dl className="grid gap-3">
              {g.buttons.map((b) => (
                <div key={b.label}>
                  <dt>
                    <Rich p={`[[${b.label}]]`} f={f} />
                  </dt>
                  <dd className="mt-1">
                    <Rich p={b.does} f={f} />
                    {b.doesNot ? (
                      <>
                        {" "}
                        <span className="text-basalt/70">
                          <Rich p={b.doesNot} f={f} />
                        </span>
                      </>
                    ) : null}
                  </dd>
                </div>
              ))}
            </dl>
            {g.note ? (
              <p className="note">
                <Rich p={g.note} f={f} />
              </p>
            ) : null}
          </Part>
        </div>
      </PageShell>
    );
  }

  const a = ARTICLES[slug];
  if (!a) notFound();
  const drawings: Record<string, ReactNode> = { states: <StateDrawing />, level: <LadderDrawing levels={f.levels} /> };
  return (
    <PageShell
      stage="Guide"
      title={a.title}
      purpose={a.purpose}
      action={
        <Link href="/guide" className="btn">
          Start here
        </Link>
      }
      next={nextAfter(here)}
    >
      <GuideNav here={here} />
      <div className="grid gap-8">
        {a.sections.map((s) => (
          <Part key={s.id} id={s.id} title={<Rich p={s.title} f={f} />}>
            {s.paras.map((p) => (
              <p key={p}>
                <Rich p={p} f={f} />
              </p>
            ))}
            {drawings[s.id]}
          </Part>
        ))}
      </div>
    </PageShell>
  );
}

/** A child's states in the school's order, each in its colour with its mark and words: the rows themselves. */
async function StateDrawing() {
  const states = await childStates();
  return (
    <figure className="m-0" data-drawing="states">
      <ol className="grid gap-2">
        {states.list.map((s) => (
          <li key={s.code} className="flex items-center gap-3 text-[14px]">
            <Swatch colour={s.colour} />
            <span className="font-medium">{s.words}</span>
            <span className="text-basalt/60">shows as {states.colours[s.colour].count_words}</span>
          </li>
        ))}
      </ol>
      <figcaption className="note mt-2">Read from the school&rsquo;s own list of states, in its order.</figcaption>
    </figure>
  );
}
