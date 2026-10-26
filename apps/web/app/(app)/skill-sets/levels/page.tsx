import Link from "@/components/link";
import { Count } from "@/components/count";
import { DataTable } from "@/components/data-table";
import { EmptyState } from "@/components/empty-state";
import { FilterBar } from "@/components/filter-bar";
import { PageShell } from "@/components/page-shell";
import { StatusChip, type State } from "@/components/status-chip";
import { requireStaff } from "@/lib/auth";
import { deadline } from "@/lib/deadline";
import { isSuggestion, levelRows, saidOf, type LevelRow } from "@/lib/queries-calibration";
import { scopeOf } from "@/lib/scope";
import { dateWords } from "@/lib/week";
import type { Column } from "@/lib/ux-rules";
import { lookedAt } from "./actions";

// Levels to review (goals/cal_levels_to_review.yaml). Nimish, 2026-10-26: "If 8 out of 10 people in the class are able to
// solve the advanced level for that particular grade or school, then that's not actually advanced. We'll need some section
// which gives us an understanding that certain things need to be upgraded, like a step." The page only suggests; changing a
// level is the skill's own edit page. Counted by the database from confirmed answers (`level_calibration`); a person sees
// the classes of their own scope, and a grade only when it is wholly theirs.

type Q = Record<string, string | undefined>;
const SHOW: [string, string][] = [
  ["review", "Suggestions"],
  ["few", "Not enough children yet"],
  ["looked", "Looked at"],
  ["fine", "No change suggested"],
];

const keeps = (r: LevelRow, show: string | undefined) =>
  !show ||
  (show === "review" && isSuggestion(r)) ||
  (show === "looked" && r.verdict === "review" && !!r.lookedAt) ||
  (show === "few" && r.verdict === "too_few") ||
  (show === "fine" && r.verdict === "fine");

function chip(r: LevelRow) {
  const [state, words]: [State, string] =
    r.verdict === "too_few"
      ? ["notYet", `not enough children yet (${r.assessed} of ${r.min})`]
      : r.verdict === "fine"
        ? ["fine", "no change"]
        : r.lookedAt
          ? ["done", "looked at"]
          : ["waiting", "to review"];
  return <StatusChip state={state} words={words} />;
}

export default async function LevelsToReview({ searchParams }: { searchParams: Promise<Q> }) {
  const me = await requireStaff();
  const q = await searchParams;
  const scope = scopeOf(me);
  const all = await deadline(levelRows(scope));
  const view = q.view === "grade" || q.view === "class" ? q.view : scope.classes ? "class" : "grade";
  const ofView = all.filter((r) => r.kind === view);
  const grades = [...new Map(ofView.map((r) => [r.grade, r.gradeName])).entries()];
  const classes = [...new Set(all.filter((r) => r.kind === "class").map((r) => r.scope))].sort();
  const grade = grades.some(([g]) => g === q.grade) ? q.grade : undefined;
  const section = classes.includes(q.class ?? "") ? q.class : undefined;
  const show = SHOW.some(([v]) => v === q.show) ? q.show : undefined;
  const search = (q.q ?? "").trim().toLowerCase();
  const shown = ofView.filter(
    (r) =>
      (!grade || r.grade === grade) &&
      (!section || view !== "class" || r.scope === section) &&
      keeps(r, show) &&
      (!search || r.skillName.toLowerCase().includes(search) || r.topicName.toLowerCase().includes(search)),
  );
  const suggestions = all.filter(isSuggestion).length;
  const few = all.filter((r) => r.verdict === "too_few").length;
  const href = `/skill-sets/levels?${new URLSearchParams(Object.entries(q).flatMap(([k, v]) => (v ? [[k, v]] : [])))}`;

  const topics = [...new Map(shown.map((r) => [r.topic, r.topicName])).entries()];
  const columns: Column<LevelRow>[] = [
    { key: "level", label: "Level", value: (r) => r.difficulty, width: "7rem" },
    { key: "counts", label: "Secure", value: (r) => `${r.secure} of ${r.assessed}`, num: true, width: "6rem" },
    {
      key: "said",
      label: "What was counted",
      value: (r) => saidOf(r),
      cell: (r) => {
        const said = saidOf(r);
        const at = r.verdict === "review" && !r.lookedAt ? said.indexOf(r.skillName) : -1;
        return (
          <>
            {at >= 0 ? (
              <>
                {said.slice(0, at)}
                <Link href={`/skill-sets/${r.skill}`}>{r.skillName}</Link>
                {said.slice(at + r.skillName.length)}
              </>
            ) : (
              said
            )}
            {r.lookedAt ? ` Looked at by ${r.lookedBy} on ${dateWords(r.lookedAt.slice(0, 10))}.` : ""}
          </>
        );
      },
    },
    { key: "status", label: "Status", value: (r) => r.verdict, cell: chip, status: true, width: "15rem" },
    {
      key: "do",
      label: "",
      value: (r) => (isSuggestion(r) ? "act" : ""),
      cell: (r) =>
        isSuggestion(r) ? (
          <span className="flex flex-wrap items-center gap-2">
            <form action={lookedAt}>
              <input type="hidden" name="kind" value={r.kind} />
              <input type="hidden" name="scope" value={r.scope} />
              <input type="hidden" name="skill" value={r.skill} />
              <input type="hidden" name="difficulty" value={r.difficulty} />
              <input type="hidden" name="back" value={href} />
              <button type="submit" className="btn secondary">
                I&apos;ve looked at this
              </button>
            </form>
            <Link href={`/skill-sets/${r.skill}/edit`}>Open the skill</Link>
          </span>
        ) : null,
      width: "17rem",
    },
  ];

  return (
    <PageShell
      stage="Curriculum"
      title="Levels to review"
      purpose="Levels that most children are already secure at, so they may be too easy. The system only suggests; you decide."
      action={
        <p className="text-[14px]" data-ux="summary">
          <Count of="levels to review" n={suggestions} /> {suggestions === 1 ? "suggestion" : "suggestions"}
          {few ? ` · ${few} ${few === 1 ? "level has" : "levels have"} not enough children yet` : ""}
        </p>
      }
      next={{ href: "/skill-sets/approve", label: "Skills to approve" }}
    >
      <FilterBar
        action="/skill-sets/levels"
        filters={[
          { name: "view", label: "Count", value: q.view === "grade" || q.view === "class" ? q.view : undefined, all: scope.classes ? "By class" : "By grade", options: [["grade", "By grade"], ["class", "By class"]] },
          { name: "grade", label: "Grade", value: grade, all: "Every grade", options: grades },
          ...(view === "class" ? [{ name: "class", label: "Class", value: section, all: "Every class", options: classes.map((c): [string, string] => [c, c]) }] : []),
          { name: "show", label: "Show", value: show, all: "Everything assessed", options: SHOW },
        ]}
        search={{ name: "q", value: q.q, placeholder: "Search a skill or topic" }}
      />
      {shown.length === 0 ? (
        <EmptyState>
          {all.length === 0
            ? "No level has been assessed yet, so there is nothing to compare. Suggestions appear as confirmed answers come in."
            : "Nothing matches these choices."}
        </EmptyState>
      ) : (
        <div className="grid gap-3">
          {topics.map(([topic, topicName]) => {
            const inTopic = shown.filter((r) => r.topic === topic);
            const skills = [...new Map(inTopic.map((r) => [r.skill, r.skillName])).entries()];
            const waiting = inTopic.filter(isSuggestion).length;
            return (
              <details key={topic} data-topic={topic} open={inTopic.some((r) => r.verdict === "review")} className="border border-basalt/12 px-3 py-2">
                <summary className="cursor-pointer text-[15px]">
                  {topicName}
                  <span className="note">
                    {" "}
                    · {skills.length} {skills.length === 1 ? "skill" : "skills"}
                    {waiting ? ` · ${waiting} to review` : ""}
                  </span>
                </summary>
                <div className="mt-2 grid gap-2">
                  {skills.map(([code, name]) => {
                    const rows = inTopic.filter((r) => r.skill === code);
                    const n = rows.filter(isSuggestion).length;
                    return (
                      <details key={code} data-skill={code} open={rows.some((r) => r.verdict === "review")} className="border-t border-basalt/10 pt-2">
                        <summary className="cursor-pointer text-[14px]">
                          {name}
                          {n ? <span className="note"> · {n} to review</span> : null}
                        </summary>
                        <div className="mt-2">
                          <DataTable
                            label={`${name} levels`}
                            columns={columns}
                            rows={rows}
                            rowKey={(r) => `${r.kind}:${r.scope}:${r.difficulty}`}
                            more={{ by: (r) => (r.kind === "grade" ? r.gradeName : `Class ${r.scope}`) }}
                          />
                          <p className="mt-1 text-[13px]">
                            <Link href={`/skill-sets/${code}`}>About this skill</Link>
                          </p>
                        </div>
                      </details>
                    );
                  })}
                </div>
              </details>
            );
          })}
        </div>
      )}
    </PageShell>
  );
}
