import Link from "@/components/link";
import { Body, Notice, PageHeader, Panel } from "@/components/shell";
import { requireStaff } from "@/lib/auth";
import { engineGet, engineSend } from "@/lib/engine";
import { isoWeek } from "@/lib/week";
import { confirmWeek } from "./actions";

type Props = { params: Promise<{ section: string }>; searchParams: Promise<Record<string, string | undefined>> };
type Row = { code: string; about: string; yes: number | null; ticked: boolean };
type Declared = { note: string; skill_sets: string[]; by: string; created_at: string };

// N4 — the week's declaration (goals/n4-week-declaration.yaml). The educator says in their own words what the class
// did this week; the engine proposes which of the grade's skill sets it covered, ticked where it is sure enough; the
// educator confirms or changes the ticks. The week's papers are made from what they confirm.
async function declared(section: string, week: string): Promise<Declared | null> {
  try {
    const res = await engineGet(`/week/${encodeURIComponent(section)}/${week}/declaration`);
    return res.ok ? ((await res.json()) as Declared) : null;
  } catch {
    return null;
  }
}

async function proposal(section: string, note: string): Promise<{ skill_sets: Row[]; why: string } | string> {
  try {
    const res = await engineSend("/week/declaration/propose", { section, note });
    if (!res.ok) return ((await res.json().catch(() => ({}))) as { detail?: string }).detail ?? "no proposal";
    return (await res.json()) as { skill_sets: Row[]; why: string };
  } catch {
    return "The engine could not be reached. Nothing was proposed.";
  }
}

export default async function WeekDeclaration({ params, searchParams }: Props) {
  await requireStaff();
  const [{ section: raw }, q] = await Promise.all([params, searchParams]);
  const section = decodeURIComponent(raw);
  const week = isoWeek();
  const note = (q.note ?? "").slice(0, 2000);
  const [now, proposed] = await Promise.all([declared(section, week), note ? proposal(section, note) : null]);

  return (
    <>
      <PageHeader
        stage="Make papers"
        title={`${section} · this week`}
        sub={`Week ${week}. Say in your own words what the class did; the engine proposes the skills it covered, and you confirm.`}
      />
      <Body>
        {q.confirmed ? <Notice tone="neem">This week is declared in your name. Its papers are made from it.</Notice> : null}
        {q.error ? <Notice tone="terracotta">{q.error}</Notice> : null}
        <div className="mb-[18px]">
          <Link href={`/make/${encodeURIComponent(section)}`} className="chip">
            ← {section}&rsquo;s papers
          </Link>
        </div>
        {now ? (
          <Panel title="Declared for this week" aside={`by ${now.by}`}>
            <p className="text-[14px]">{now.note || "No note."}</p>
            <p className="mt-2 text-[14px]">Skills: {now.skill_sets.join(", ")}</p>
          </Panel>
        ) : null}
        <div className="h-[18px]" />
        <Panel title={now ? "Declare it again" : "What did the class do this week?"}>
          <form method="get" className="grid gap-2">
            <textarea name="note" defaultValue={note} rows={3} maxLength={2000} className="input" placeholder="e.g. exchanging in 2-digit subtraction, and a few story sums" />
            <div>
              <button className="btn" type="submit">
                Propose the skills
              </button>
            </div>
          </form>
          {typeof proposed === "string" ? <p className="mt-3 text-[14px]">{proposed}</p> : null}
          {proposed && typeof proposed !== "string" ? (
            <form action={confirmWeek} className="mt-4 grid gap-2">
              <input type="hidden" name="section" value={section} />
              <input type="hidden" name="week" value={week} />
              <input type="hidden" name="note" value={note} />
              <input type="hidden" name="proposed" value={JSON.stringify(proposed.skill_sets.map(({ code, yes, ticked }) => ({ code, yes, ticked })))} />
              {proposed.why ? <p className="text-[14px]">Nothing is ticked ({proposed.why}); tick the skills yourself.</p> : null}
              {proposed.skill_sets.map((r) => (
                <label key={r.code} className="flex items-start gap-2 text-[14px]">
                  <input type="checkbox" name="skill_set" value={r.code} defaultChecked={r.ticked} className="mt-1" />
                  <span>
                    {r.about}
                    {r.yes !== null ? <span className="text-[12.5px] opacity-70"> · {Math.round(r.yes * 100)}% sure</span> : null}
                  </span>
                </label>
              ))}
              <div>
                <button className="btn" type="submit">
                  Confirm the week
                </button>
              </div>
            </form>
          ) : null}
        </Panel>
      </Body>
    </>
  );
}
