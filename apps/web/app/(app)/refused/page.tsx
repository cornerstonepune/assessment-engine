import Link from "next/link";
import { Body, PageHeader } from "@/components/shell";
import { requireStaff } from "@/lib/auth";
import { decidersOf, KIND_WORDS, type Kind } from "@/lib/decides";
import { ROLE_WORDS } from "@/lib/queries-people";
import { deadline } from "@/lib/deadline";
import { PAPER_NOT_YOURS } from "@/components/not-yours";

type Props = { searchParams: Promise<Record<string, string | undefined>> };

// Where a refused decision lands (goals/f1c-who-decides-what.yaml): whose decision it is, or that the class is not the
// signer's. Nothing was written.
export default async function Refused({ searchParams }: Props) {
  await requireStaff();
  const q = await searchParams;
  const kind = (q.kind && q.kind in KIND_WORDS ? q.kind : null) as Kind | null;
  const roles = kind === "asks" && q.role && q.role in ROLE_WORDS ? [q.role] : kind ? await deadline(decidersOf(kind)) : null;
  const who = [...(roles ?? []), "coordinator"].filter((r, i, all) => all.indexOf(r) === i).map((r) => ROLE_WORDS[r] ?? r);
  const what = kind ? KIND_WORDS[kind] : "That decision";
  return (
    <>
      <PageHeader stage="Not changed" title="Nothing was changed" sub="A decision on the site is taken by the people the school names for it." />
      <Body>
        <p role="status" className="max-w-[62ch]">
          {q.paper
            ? PAPER_NOT_YOURS
            : q.class
            ? `${what}: that is not one of your classes. The coordinator links you to the classes you teach.`
            : `${what} is a decision for ${who.join(" or ")}.`}
        </p>
        <p className="mt-3">
          <Link href="/today" className="underline underline-offset-2">
            Back to Today
          </Link>
        </p>
      </Body>
    </>
  );
}
