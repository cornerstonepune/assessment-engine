import type { ReactNode } from "react";
import Link from "@/components/link";
import { notFound } from "next/navigation";
import { Answers, KIND, Mistakes, Question } from "@/components/question";
import { Body, PageHeader, Panel, Pill } from "@/components/shell";
import { RULE_WORDS } from "@/lib/queries";
import { mistakeBook, paperItems, printedPaper, type PrintedPaper } from "@/lib/queries-bank";
import { deadline } from "@/lib/deadline";
import { LIBRARY_CODE, LibraryWorksheetPage } from "./library-sheet";

type Props = { params: Promise<{ qr: string }> };

// One paper, end to end: the page as it was printed, how the engine drew it from the bank, and the
// key it is marked against. Every sentence is filled from the paper's own rows.
export default async function PaperPage({ params }: Props) {
  const { qr } = await params;
  // A library worksheet (R5-H07) or a child's printed paper (CS + six hex): one address for both.
  if (LIBRARY_CODE.test(qr)) return <LibraryWorksheetPage code={qr} />;
  if (!/^CS[0-9A-F]{6}$/.test(qr)) notFound();
  const [p, questions, book] = await deadline(Promise.all([printedPaper(qr), paperItems(qr), mistakeBook()]));
  if (!p) notFound();
  const back = p.section ? `/worksheets?section=${p.section}&week=${p.week}&kind=${p.kind}` : "/worksheets";

  return (
    <>
      <PageHeader
        stage="Stage 2 · Print"
        title={`Paper ${p.qr_code}`}
        sub="The printed page, how it was made, and its answer key."
      />
      <Body>
        <Link href={back} className="mb-4 inline-block text-[13px]">
          ← All papers for {p.section ?? "this week"} · {p.week}
        </Link>
        <div className="grid gap-[18px] lg:grid-cols-[minmax(0,1fr)_400px]">
          <Panel title="The page as printed" aside={`${p.pages} ${p.pages === 1 ? "page" : "pages"}`}>
            {p.rendered ? (
              Array.from({ length: p.pages }, (_, i) => (
                <figure key={i} className="mb-3 last:mb-0">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={`/api/paper/${p.qr_code}/${i + 1}`}
                    alt={`Page ${i + 1} of paper ${p.qr_code}, as printed`}
                    className="w-full border border-basalt/14 bg-white"
                  />
                </figure>
              ))
            ) : (
              <p className="note">
                This paper has not been turned into a printable page yet, so there is nothing to show here. Its questions and
                answers are below.
              </p>
            )}
          </Panel>

          <Panel title="How it was made">
            <dl className="grid gap-[14px] text-[13.5px] leading-[1.5]">
              {facts(p).map(([label, value]) => (
                <div key={label}>
                  <dt className="label mb-[3px]">{label}</dt>
                  <dd>{value}</dd>
                </div>
              ))}
            </dl>
          </Panel>
        </div>

        <div className="mt-[18px]">
          <Panel title="The answer key" aside={`${questions.length} questions`}>
            <div className="overflow-x-auto">
              <table className="grid" aria-label="Answer key">
                <thead>
                  <tr>
                    <th className="text-right">#</th>
                    <th>Question</th>
                    <th>Kind</th>
                    <th>Answer</th>
                    <th>Wrong answers it catches</th>
                  </tr>
                </thead>
                <tbody>
                  {questions.map((it, i) => (
                    <tr key={it.item_key}>
                      <td className="num">{i + 1}</td>
                      <td className="min-w-[200px] max-w-[420px]">
                        <Link href={`/library/${it.item_key}`} className="block text-basalt hover:text-terracotta">
                          <Question it={it} />
                        </Link>
                      </td>
                      <td className="text-[12.5px]">{KIND[it.fmt] ?? it.fmt}</td>
                      <td>
                        <Answers it={it} />
                      </td>
                      <td className="min-w-[200px] max-w-[340px]">
                        <Mistakes it={it} book={book} more={`/library/${it.item_key}`} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Panel>
        </div>
      </Body>
    </>
  );
}

// A paper's facts, in the order they happened, one line each.
function facts(p: PrintedPaper): [string, ReactNode][] {
  const pool = p.pool.toLocaleString("en-IN");
  return [
    ["For", p.roll_no ? `Roll ${p.roll_no} · ${p.section} · ${p.week} ${p.kind}` : "A spare copy, no name — for a late child or a spoilt page"],
    [
      "Tests",
      <>
        {p.skill_set_name} · <Pill tone="monsoon">{p.difficulty ?? "each at the child's own level"}</Pill>
        {p.rule_fired ? (
          <span className="note block">
            {RULE_WORDS[p.rule_fired] ?? p.rule_fired}
            {p.override_reason ? ` “${p.override_reason}”` : ""}
          </span>
        ) : null}
      </>,
    ],
    [
      "Questions",
      p.source === "focus" ? (
        `${p.n_items} chosen from this child's own checked papers — the areas they lag in, at their level, none they had been given before`
      ) : p.worksheet ? (
        <>
          Worksheet <Link href={`/worksheets/${p.worksheet}`}>{p.worksheet}</Link> from the library, one of {p.worksheets} at this
          level —{" "}
          {p.roll_no
            ? `never sat by this child, none of its ${p.n_items} questions seen in ${p.window_days} days, none on a classmate's paper this week`
            : "not given to a named child this week"}
        </>
      ) : p.roll_no ? (
        `${p.n_items} picked at random from ${pool} at this level — none this child saw in ${p.window_days} days, none shared with a classmate`
      ) : (
        `${p.n_items} picked at random from ${pool} at this level — none given to a named child this week`
      ),
    ],
    [
      "QR code",
      p.roll_no
        ? `${p.qr_code} on every page. It points to this record: the child, the questions and their answers.`
        : `${p.qr_code} on every page. It points to this record: the questions and their answers. The child writes their name.`,
    ],
    ["Status", p.print_status === "printed" ? `Approved by ${p.approved_by}` : "Waiting for a teacher to approve the pack"],
  ];
}
