import type { ReactNode } from "react";
import Link from "@/components/link";
import { GROUPS } from "@/lib/menu";
import { slugOf } from "@/lib/guide-path";
import { GUIDE_ORDER, STEP_GUIDE, pieces, type Area, type Facts, type Para } from "@/lib/guide";
import { STEPS, WORKFLOWS } from "@/lib/workflows";

// The Guide's drawings and its words (goals/guide_for_educators.yaml). Every drawing is made from what the site runs on,
// never a screenshot: the flow from workflows.json, the menu from lib/menu.ts, a page's layout from its guide file, the
// ladder from the school's levels. Each drawing is hidden from a screen reader and said again as a list beside it, and
// no meaning is carried by colour alone.

/** A paragraph of the guide, its tokens filled from the rows: a button's label set as a key, a link as a link. */
export function Rich({ p, f }: { p: Para; f: Facts }) {
  return (
    <>
      {pieces(p, f).map((x, i) =>
        "button" in x ? (
          <strong key={i} className="whitespace-nowrap border border-basalt/25 bg-chalk px-[5px] py-[1px] text-[0.92em] font-medium">
            {x.button}
          </strong>
        ) : "link" in x ? (
          <Link key={i} href={x.href}>
            {x.link}
          </Link>
        ) : (
          <span key={i}>{x.text}</span>
        ),
      )}
    </>
  );
}

/** A section of a guide page: a real heading, its address for "?" links and "I want to" buttons. */
export function Part({ id, title, children }: { id: string; title: ReactNode; children: ReactNode }) {
  return (
    <section id={id} aria-labelledby={`${id}-h`} className="scroll-mt-6 border-t border-basalt/12 pt-5">
      <h2 id={`${id}-h`} className="mb-3 text-[18px]">
        {title}
      </h2>
      <div className="grid max-w-[720px] gap-3 text-[15px] leading-[1.6]">{children}</div>
    </section>
  );
}

/** The guide's own contents, on every guide page: where you are, and every other page of it. */
export function GuideNav({ here }: { here: string }) {
  return (
    <nav aria-label="The guide" className="mb-6">
      <ul className="flex flex-wrap gap-x-4 gap-y-1 text-[13.5px]">
        {GUIDE_ORDER.map((g) => (
          <li key={g.href}>
            <Link href={g.href} aria-current={g.href === here ? "page" : undefined} className={`inline-flex min-h-9 items-center ${g.href === here ? "font-medium text-basalt no-underline" : ""}`}>
              {g.label}
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}

/** Each step's place in the week: the stages in order, and the steps in each stage in order. */
const NUMBER = new Map(WORKFLOWS.flatMap((w) => w.steps).map((code, i) => [code, i + 1]));

const ARROW = (
  <span aria-hidden="true" className="self-center text-[20px] text-basalt/40 max-md:rotate-90 max-md:justify-self-center">
    →
  </span>
);

/** The school's whole flow: the four stages of workflows.json in order, each with its steps, numbered as the week runs. */
export function FlowDrawing({ link = true }: { link?: boolean }) {
  return (
    <figure className="m-0" data-drawing="flow">
      <div className="grid gap-3 md:grid-cols-[1fr_auto_1fr_auto_1fr_auto_1fr]">
        {WORKFLOWS.map((w, i) => (
          <div key={w.code} className="contents">
            {i ? ARROW : null}
            <section aria-label={w.name} className="panel min-w-0 p-3" data-stage={w.code}>
              <h3 className="label mb-2 !text-monsoon">{w.name}</h3>
              <ol className="grid gap-2">
                {w.steps.map((code) => {
                  const s = STEP_GUIDE[code];
                  return (
                    <li key={code} className="flex gap-2 text-[13.5px]" data-step={code}>
                      <span className="fact w-5 shrink-0 text-right text-basalt/55">{NUMBER.get(code)}</span>
                      {link ? <Link href={`/guide/workflows#${code}`}>{s.name}</Link> : <span>{s.name}</span>}
                    </li>
                  );
                })}
              </ol>
            </section>
          </div>
        ))}
      </div>
      <figcaption className="note mt-2">Drawn from the map the engine&rsquo;s code is held to, so it changes when the steps do.</figcaption>
    </figure>
  );
}

/** The menu as it is: the groups across the top bar, each group's pages under it, each opening its guide page. */
export function MenuDrawing() {
  return (
    <figure className="m-0" data-drawing="menu">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {GROUPS.map((g) => (
          <section key={g.key} aria-label={g.label} className="min-w-0 border border-basalt/15">
            <h3 className="bg-basalt px-3 py-2 text-[14px] font-normal text-lime">{g.label}</h3>
            <ul className="grid p-2">
              {g.pages.map((p) => (
                <li key={p.href}>
                  <Link href={`/guide/${slugOf(p.label)}`} className="inline-flex min-h-9 items-center text-[14px]">
                    {p.label}
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>
      <figcaption className="note mt-2">The top bar&rsquo;s groups, and the pages inside each. Drawn from the site&rsquo;s own menu.</figcaption>
    </figure>
  );
}

/** A page of the site drawn as boxes, numbered, with the same numbers in the list beside it that says what each shows. */
export function PageDrawing({ title, layout, f }: { title: string; layout: Area[]; f: Facts }) {
  return (
    <div className="grid gap-4 md:grid-cols-[minmax(0,300px)_1fr]" data-drawing="page">
      <div aria-hidden="true" className="border border-basalt/25 bg-chalk">
        <div className="flex items-center gap-2 bg-basalt px-2 py-[6px] text-[11px] text-lime">
          <span className="h-3 w-3 rounded-full bg-lime/70" />
          <span>top bar</span>
        </div>
        <div className="border-b border-basalt/15 px-2 py-2 text-[12px] font-medium">{title}</div>
        <ol className="grid gap-[6px] p-2">
          {layout.map((a, i) => (
            <li key={a.area} className={`flex items-center gap-2 border border-dashed border-basalt/35 px-2 text-[11.5px] text-basalt/70 ${i === layout.length - 1 ? "py-2" : "py-3"}`}>
              <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-basalt text-[11px] text-chalk">{i + 1}</span>
              {a.area}
            </li>
          ))}
        </ol>
      </div>
      <ol className="grid content-start gap-3 text-[14.5px] leading-[1.55]">
        {layout.map((a, i) => (
          <li key={a.area} className="flex gap-3">
            <span aria-hidden="true" className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-basalt text-[12px] text-chalk">
              {i + 1}
            </span>
            <span>
              <strong className="font-medium">{a.area}.</strong> <Rich p={a.shows} f={f} />
            </span>
          </li>
        ))}
      </ol>
    </div>
  );
}

/** The school's levels as a ladder, easiest at the bottom left, read from the levels rows. */
export function LadderDrawing({ levels }: { levels: string[] }) {
  return (
    <figure className="m-0" data-drawing="ladder">
      <div aria-hidden="true" className="flex items-end gap-2">
        {levels.map((l, i) => (
          <div key={l} className="flex min-w-0 max-w-24 flex-1 items-end justify-center border border-basalt/30 bg-bamboo/25 pb-1 text-[12.5px]" style={{ height: 28 + i * 18 }}>
            {l}
          </div>
        ))}
      </div>
      <figcaption className="note mt-2">The school&rsquo;s levels, easiest first: {levels.join(", ")}.</figcaption>
    </figure>
  );
}

/** Each step of the school's flow, with who does it and what they see, in the order of the drawing. */
export function StepList({ f }: { f: Facts }) {
  const byCode = new Map(STEPS.map((s) => [s.code, s]));
  return (
    <>
      {WORKFLOWS.map((w) => (
        <Part key={w.code} id={`stage-${w.code}`} title={w.name}>
          <ol className="grid gap-4">
            {w.steps.map((code) => {
              const s = STEP_GUIDE[code];
              const built = byCode.get(code)?.built;
              return (
                <li key={code} id={code} className="scroll-mt-6" data-step={code}>
                  <h3 className="text-[15.5px] font-medium">
                    {NUMBER.get(code)}. {s.name}
                    {built && built !== "live" ? <span className="ml-2 text-[13px] font-normal text-basalt/60">({built === "partly" ? "partly built" : "not built yet"})</span> : null}
                  </h3>
                  <p className="text-[13px] text-basalt/65" data-who>
                    Who: {s.who.join(", ")}
                  </p>
                  <p>
                    <Rich p={s.sees} f={f} />
                  </p>
                </li>
              );
            })}
          </ol>
        </Part>
      ))}
    </>
  );
}
