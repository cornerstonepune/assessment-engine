import Link from "@/components/link";
import { DataTable } from "@/components/data-table";
import type { TopicGroup } from "@/lib/queries-by-topic";
import type { PaperListRow } from "@/lib/queries-papers";
import type { Column } from "@/lib/ux-rules";
import { AssessmentsTable, type Named } from "./assessments-table";

// The assessments by topic (goals/asm2_by_topic_and_checking.yaml): every topic a row with its count, closed until it is
// opened; the open one holds the table of its assessments, one page of them. A topic is opened by its address, so the view
// can be sent to a colleague, and no other topic's rows are read.
export async function ByTopic({
  groups,
  subjects,
  open,
  rows,
  of,
  copies,
  pages,
  page,
  topicPage,
  back,
  topicHref,
  assessmentHref,
  assessmentsPageHref,
  topicsPageHref,
}: {
  groups: TopicGroup[];
  subjects: Map<string, string>;
  open?: string;
  /** The open topic's assessments: just the page asked for. */
  rows: Named[];
  of: number;
  copies: Map<string, PaperListRow[]>;
  pages: Map<string, { capture: string; pages: number[] }>;
  page: number;
  topicPage: number;
  back: string;
  topicHref: (code: string, isOpen: boolean) => string;
  assessmentHref: (a: Named, isOpen: boolean) => string;
  assessmentsPageHref: (n: number) => string;
  topicsPageHref: (n: number) => string;
}) {
  const columns: Column<TopicGroup>[] = [
    {
      key: "topic",
      label: "Topic",
      width: "40%",
      keep: true,
      value: (g) => g.name,
      cell: (g) => (
        <Link
          href={topicHref(g.code, g.code === open)}
          aria-expanded={g.code === open}
          className={`font-medium text-basalt before:mr-1 before:inline-block before:w-3 before:text-basalt/50 ${g.code === open ? "before:content-['▾']" : "before:content-['▸']"}`}
        >
          {g.name}
        </Link>
      ),
    },
    {
      key: "subject",
      label: "Subject",
      width: "20%",
      value: (g) => (g.subject ? (subjects.get(g.subject) ?? g.subject) : null),
    },
    {
      key: "total",
      label: "Assessments",
      width: "18%",
      num: true,
      keep: true,
      value: (g) => g.total,
    },
    {
      key: "needYou",
      label: "Waiting on you",
      width: "22%",
      num: true,
      value: (g) => g.needYou,
    },
  ];
  return (
    <DataTable
      label="Assessments by topic"
      columns={columns}
      rows={groups}
      rowKey={(g) => g.code}
      more={{ page: topicPage, href: topicsPageHref }}
      extras={{
        attrs: (g) => ({
          "data-topic": g.code,
          "data-open": String(g.code === open),
        }),
        expand: (g) =>
          g.code === open ? (
            <div data-topic-rows={g.code}>
              <AssessmentsTable
                rows={rows}
                of={of}
                copies={copies}
                pages={pages}
                page={page}
                back={back}
                href={assessmentHref}
                pageHref={assessmentsPageHref}
              />
              {rows.length === 0 ? (
                <p className="note mt-2">
                  Nothing in {g.name} matches these filters.
                </p>
              ) : null}
            </div>
          ) : null,
      }}
    />
  );
}
