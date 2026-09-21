import NextLink from "next/link";
import type { ComponentProps } from "react";

// A link that does not load its page in advance. Next pre-loads every link on screen in production,
// and the Skill Map alone holds 85 of them: one opening of it started 85 page loads against the
// database at once. Only the six menu links (components/nav.tsx) pre-load; every link on a page is
// this one. A page still shows its loading screen the moment it is clicked (app/(app)/loading.tsx).
export default function Link(props: ComponentProps<typeof NextLink>) {
  return <NextLink prefetch={false} {...props} />;
}
