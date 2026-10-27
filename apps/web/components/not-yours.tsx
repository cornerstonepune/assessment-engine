import Link from "next/link";
import { Body, PageHeader } from "./shell";

/** What an educator reads for a paper, scan or answer they do not see (goals/own_who_sees_answers.yaml). */
export const PAPER_NOT_YOURS = "This paper belongs to another class. Nothing of it is shown, and nothing was changed.";

/** What a page for another class shows an educator (goals/f1b-my-classes-first.yaml): that it is not theirs, and
 *  nothing of it — no child's name, no paper, no answer. */
export function NotYours({ what, paper }: { what: string; paper?: boolean }) {
  return (
    <>
      <PageHeader stage="Your classes" title="Not one of your classes" sub="The coordinator links you to the classes you teach." />
      <Body>
        <p className="max-w-[60ch]">{paper ? PAPER_NOT_YOURS : `${what} is not one of your classes.`}</p>
        <p className="mt-3">
          <Link href="/today" className="underline underline-offset-2">
            Back to Today
          </Link>
        </p>
      </Body>
    </>
  );
}
