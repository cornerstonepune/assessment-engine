import { requireStaff } from "@/lib/auth";
import { Shell } from "@/components/shell";
import { deadline } from "@/lib/deadline";
import { counts, needsYou } from "@/lib/needs-you";
import { gradeSpan } from "@/lib/queries";

export const dynamic = "force-dynamic";

// Every route in this group is behind the staff gate. Actions check again on their own. The menu carries, on every
// page, the count of what waits in each tab: Today's own list (goals/ui1-menu-and-today.yaml).
export default async function AppLayout({ children }: LayoutProps<"/">) {
  const me = await requireStaff();
  const [lines, span] = await deadline(Promise.all([needsYou(me), gradeSpan()]));
  return <Shell me={me} waiting={counts(lines)} grades={span}>{children}</Shell>;
}
