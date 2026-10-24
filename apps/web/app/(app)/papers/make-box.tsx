import Link from "@/components/link";

// The four ways an educator makes an assessment (goals/asm_assessments_page.yaml), each opening the maker ready for that use.
// Nimish, 2026-10-11: "for every child, there is a customized assessment and the capability to create their own
// assessments or generate assessments as and when required for a particular class".
const STARTS: [string, string, string][] = [
  ["For a class", "/papers/make?kind=assessment&way=same", "One assessment for every child of a class: choose the class, then a topic or the skills."],
  ["For each child", "/make", "This week's home assessment for each child, made from their own record, to approve."],
  ["For one child", "/papers/make?kind=assessment&way=own&one=1", "A follow-up for one child: the engine proposes their next step, and you can change it."],
  ["A ready-made worksheet", "/worksheets", "A worksheet from the library, printed for the children you choose."],
];

export function MakeBox() {
  return (
    <section aria-label="Make an assessment" className="panel flex min-w-0 flex-col gap-2 p-4">
      <h2 className="label">Make an assessment</h2>
      <div className="grid flex-1 gap-2 sm:grid-cols-2">
        {STARTS.map(([title, href, words]) => (
          <Link key={title} href={href} title={words} className="flex items-center border border-basalt/25 bg-chalk px-3 py-3 font-heading text-[15px] text-basalt no-underline hover:border-basalt">
            {title}
          </Link>
        ))}
      </div>
    </section>
  );
}
