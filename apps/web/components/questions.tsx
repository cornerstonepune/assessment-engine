import Link from "@/components/link";

// A paper's questions on screen before anything prints (goals/preview-before-print.yaml). Nimish, 2026-10-21: "a
// teacher can only see the assessment when they print. They click on print just to see the assessment". Every page
// that makes a paper shows its questions under their skill and level, offers different ones, and prints what it showed.

/** One skill's questions on a paper, in the order they print, under the skill and level they are. */
export function Questions({ name, level, questions }: { name: string; level: string; questions: { item_key: string; text: string }[] }) {
  return (
    <ol aria-label={`${name} · ${level}`} className="mt-2 grid list-decimal gap-1 pl-5 text-[13px]">
      {questions.map((x) => (
        <li key={x.item_key} data-item={x.item_key}>
          {x.text}
        </li>
      ))}
    </ol>
  );
}

/** Draws other questions for the same skills and levels. A link, not a form: it makes nothing — no paper, no code, no
 *  approval — and the page shows the new questions before anything prints. */
export function DifferentQuestions({ href }: { href: string }) {
  return (
    <Link href={href} className="btn secondary">
      Different questions
    </Link>
  );
}

/** What a page says when the questions shown would no longer be the ones printed: a paper was made for the child
 *  meanwhile. Nothing printed; the page shows them as they are now. */
export const CHANGED =
  "Nothing was printed: the questions changed since you saw them, because a paper was made for this child meanwhile. Here they are as they are now; look them over and approve again.";
