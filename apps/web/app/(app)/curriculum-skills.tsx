import Link from "@/components/link";
import { DataTable } from "@/components/data-table";
import { StatusChip } from "@/components/status-chip";
import { type SkillLine, statusOf } from "@/lib/curriculum-list";
import type { Column } from "@/lib/ux-rules";
import { switchTopic } from "./topic-actions";

// The curriculum, a skill to a row (goals/uxn2-curriculum-table.yaml). Nimish, 2026-10-22: "the tags of subject names and
// all are never aligned, like on the curriculum page ... Can we use tables more for easier viewing". Grade, subject, topic
// and skill are columns; the state is one chip. Where a person may say a class has been taught the skill, the button is on
// its row (goals/l9-not-taught-is-said-where-it-shows.yaml).
function Say({ line }: { line: SkillLine }) {
  const classes = line.untaught;
  if (!classes.length) return null;
  return (
    <form action={switchTopic} className="mt-1 inline-flex items-center gap-1">
      <input type="hidden" name="code" value={line.topicOf} />
      <input type="hidden" name="skill" value={line.skillCode} />
      <input type="hidden" name="taught" value="on" />
      {classes.length === 1 ? (
        <input type="hidden" name="class" value={classes[0]} />
      ) : (
        <select
          name="class"
          aria-label="Class"
          className="select py-0 text-[12px]"
          defaultValue={classes[0]}
        >
          {classes.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
      )}
      <button
        type="submit"
        className="btn secondary whitespace-nowrap text-[12px]"
      >
        {classes.length === 1
          ? `Say it is taught in ${classes[0]}`
          : "Say it is taught"}
      </button>
    </form>
  );
}

export function CurriculumSkills({
  lines,
  say,
  page,
  pageHref,
}: {
  lines: SkillLine[];
  say: boolean;
  page: number;
  pageHref: (page: number) => string;
}) {
  const columns: Column<SkillLine>[] = [
    {
      key: "grade",
      label: "Grade",
      width: "6.5rem",
      keep: true,
      value: (l) => l.grade,
    },
    {
      key: "subject",
      label: "Subject",
      width: "7rem",
      keep: true,
      value: (l) => l.subject,
    },
    {
      key: "topic",
      label: "Topic",
      width: "12rem",
      keep: true,
      value: (l) => l.topic,
    },
    {
      key: "skill",
      label: "Skill",
      keep: true,
      value: (l) => l.skill,
      cell: (l) => (
        <>
          <Link href={l.href}>{l.skill}</Link>
          {l.notTaught && say ? (
            <div>
              <Say line={l} />
            </div>
          ) : null}
        </>
      ),
    },
    {
      key: "levels",
      label: "Levels",
      width: "13rem",
      keep: true,
      value: (l) => l.levels.join(" · "),
    },
    {
      key: "status",
      label: "Status",
      width: "11rem",
      status: true,
      keep: true,
      value: (l) => statusOf(l),
      cell: (l) => <StatusChip state={statusOf(l)} />,
    },
  ];
  return (
    <DataTable
      label="The curriculum"
      columns={columns}
      rows={lines}
      rowKey={(l) => l.id}
      more={{ page, href: pageHref }}
      extras={{
        attrs: (l) => ({
          "data-skill": l.skillCode,
          "data-grade": l.gradeCode,
        }),
      }}
    />
  );
}
