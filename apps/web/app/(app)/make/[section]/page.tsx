import Link from "@/components/link";
import { FilterBar } from "@/components/filter-bar";
import { Notice } from "@/components/shell";
import { PageShell } from "@/components/page-shell";
import type { State } from "@/components/status-chip";
import { requireStaff } from "@/lib/auth";
import { NotYours } from "@/components/not-yours";
import { isMine, reachOf, scopeOf } from "@/lib/scope";
import { deadline } from "@/lib/deadline";
import { staffList } from "@/lib/queries";
import { readDraw } from "@/lib/next-paper";
import { CHANGED } from "@/components/questions";
import { classHome } from "@/lib/queries-make";
import { classPacksWaiting } from "@/lib/queries-today";
import { isoWeek, weekWords } from "@/lib/week";
import { approveHome } from "../actions";
import { byNeed, HomeTable, type HomeRow } from "./home-table";

type Props = { params: Promise<{ section: string }>; searchParams: Promise<Record<string, string | string[] | undefined>> };

const one = (v: string | string[] | undefined) => (Array.isArray(v) ? v[0] : v);

// One class's home papers for the week (goals/ux5b-make-and-marking.yaml): each child still waiting is one line — the
// one skill the engine proposes, why, and one next step: approve it, or choose one where the engine has nothing to go on.
// Each paper's questions are on the line before anything prints, and "Different questions" draws others for that child
// alone, making nothing (goals/preview-before-print.yaml); approving prints the questions shown. The address carries
// each child's draw as `draw=<child>~<n>`. The children already approved fold under one line.
export default async function ClassHomePapers({ params, searchParams }: Props) {
  const me = await requireStaff();
  const [{ section: raw }, q] = await Promise.all([params, searchParams]);
  const section = decodeURIComponent(raw);
  const scope = scopeOf(me);
  if (!isMine(reachOf(me), section)) return <NotYours what={section} />;
  const week = isoWeek();
  const draws: Record<string, number> = {};
  for (const d of [q.draw ?? []].flat()) {
    const [child, n] = d.split("~");
    if (child && readDraw(n)) draws[child] = readDraw(n);
  }
  // "Different questions" for one child: every other child keeps the questions on screen
  const differentFor = (id: string) => {
    const next = new URLSearchParams();
    for (const [c, n] of Object.entries({ ...draws, [id]: (draws[id] ?? 0) + 1 })) next.append("draw", `${c}~${n}`);
    return `/make/${encodeURIComponent(section)}?${next}`;
  };
  const [children, staff, packs] = await deadline(Promise.all([classHome(section, me.email, week, draws), staffList(), classPacksWaiting(scope)]));
  const name = Object.fromEntries(staff.map((s) => [s.email, s.name]));
  const proposed = children.filter((c) => !c.proposal.approved && c.proposal.areas.length);
  // how many questions a paper holds is said once when every paper holds the same
  const lengths = new Set(proposed.map((c) => c.proposal.areas[0].questions.length));
  const each = lengths.size === 1 ? [...lengths][0] : null;
  const rows: HomeRow[] = children
    .map((c) => ({
      child: c,
      state: (c.proposal.approved ? "done" : c.proposal.areas.length ? "toApprove" : "chooseOne") as State,
      approvedBy: c.proposal.approved ? (name[c.proposal.approved.approved_by] ?? c.proposal.approved.approved_by) : null,
      draw: draws[c.id] ?? 0,
    }))
    .sort(byNeed);
  const stage = one(q.status) && one(q.status)! in STAGES ? one(q.status) : undefined;
  const find = one(q.q)?.trim().toLowerCase();
  const shown = rows.filter((r) => (!stage || r.state === STAGES[stage]) && (!find || r.child.first_name.toLowerCase().includes(find)));
  const page = Math.max(1, Math.floor(Number(one(q.page))) || 1);
  const here = `/make/${encodeURIComponent(section)}`;
  const pageHref = (n: number) => `${here}?${new URLSearchParams({ ...(stage ? { status: stage } : {}), ...(find ? { q: find } : {}), page: String(n) })}`;
  const packsHere = packs.filter((p) => p.section === section);

  return (
    <PageShell
      stage="Assessments · make"
      title={`${section} · home assessments`}
      purpose={`This week, ${weekWords(week)}. Each child's home assessment works on one skill from their own map; its questions are on its line.`}
      action={
        proposed.length ? (
          <form action={approveHome}>
            <input type="hidden" name="week" value={week} />
            <input type="hidden" name="section" value={section} />
            {proposed.map((c) => (
              <span key={c.id} hidden>
                <input type="hidden" name="child_id" value={c.id} />
                <input type="hidden" name="draw" value={draws[c.id] ?? 0} />
                <input type="hidden" name="seen" value={c.proposal.seen} />
              </span>
            ))}
            <button className="btn" type="submit">
              Approve all {proposed.length}
            </button>
          </form>
        ) : (
          <Link href={`${here}/week`} className="btn secondary">
            What the class did this week
          </Link>
        )
      }
      next={{ href: "/capture", label: "Upload papers" }}
      details={proposed.length ? { href: `${here}/week`, label: "What the class did this week" } : undefined}
    >
      {one(q.approved) ? <Notice tone="neem">Approved {one(q.approved)}, in your name. They print as each child&rsquo;s home assessment.</Notice> : null}
      {one(q.changed) ? (
        <Notice tone="terracotta">
          {one(q.changed)} not printed. {CHANGED}
        </Notice>
      ) : null}
      {packsHere.map((p) => (
        <p key={`${p.week}|${p.kind}`} className="mb-3 text-[13.5px]">
          Class papers waiting for you:{" "}
          <Link href={`/papers/approve?section=${encodeURIComponent(p.section)}&week=${encodeURIComponent(p.week)}&kind=${p.kind}`}>
            {weekWords(p.week)} · {p.kind === "assessment" ? "class assessment" : "class practice"} — {p.n} papers
          </Link>
        </p>
      ))}
      <p className="note mb-3">
        {proposed.length} waiting for you{each ? ` · ${each} questions each` : ""}.{" "}
        {scope.classes?.length === 1 ? null : <Link href="/make">← Every class</Link>}
      </p>
      <FilterBar
        action={here}
        search={{ name: "q", value: find, placeholder: "Find a child" }}
        filters={[{ name: "status", label: "Status", value: stage, all: "Any status", options: Object.entries(STAGE_WORDS) }]}
      />
      <section aria-label="Home assessments">
        <HomeTable rows={shown} week={week} section={section} draws={draws} differentFor={differentFor} page={page} pageHref={pageHref} each={each} />
        {shown.length === 0 ? <p className="note mt-2">{children.length ? "Nothing matches these filters." : "No children on this class's list."}</p> : null}
      </section>
    </PageShell>
  );
}

const STAGES: Record<string, State> = { toApprove: "toApprove", approved: "done", chooseOne: "chooseOne" };
const STAGE_WORDS: Record<string, string> = { toApprove: "To approve", approved: "Approved", chooseOne: "Choose one" };
