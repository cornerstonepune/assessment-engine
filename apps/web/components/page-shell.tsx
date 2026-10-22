import Link from "@/components/link";
import { Body, PageHeader } from "./shell";

type To = { href: string; label: string };

// A page of the educator's site (rule 1, docs/ux-rules.md): its title says what it is for, one line says more, ONE main
// action is where a thumb finds it, and the page ends on the next step, so there is no dead end. `details` is where the
// setup and the numbers for a reader of statistics wait (rule 8). The slots are required props, so a page that leaves one
// out does not compile; `purpose` is held to PURPOSE_MAX by tests/test_ux_rules.py and the rendered test.
export function PageShell({
  stage,
  title,
  purpose,
  action,
  next,
  details,
  children,
}: {
  stage: string;
  title: string;
  purpose: string;
  action: React.ReactNode;
  next: To;
  details?: To;
  children: React.ReactNode;
}) {
  return (
    <>
      <PageHeader stage={stage} title={title} sub={purpose} />
      <Body>
        <div className="mb-4 flex flex-wrap items-center gap-3" data-ux="action">
          {action}
          {details ? (
            <Link href={details.href} className="ml-auto text-[13px]" data-ux="details">
              {details.label}
            </Link>
          ) : null}
        </div>
        {children}
        <nav className="mt-6 border-t border-basalt/12 pt-4" aria-label="Next step">
          <Link href={next.href} className="chip" data-ux="next">
            {next.label} →
          </Link>
        </nav>
      </Body>
    </>
  );
}
