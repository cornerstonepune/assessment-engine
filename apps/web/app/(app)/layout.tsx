import { requireStaff } from "@/lib/auth";
import { Shell } from "@/components/shell";
import { deadline } from "@/lib/deadline";
import { counts, needsYou } from "@/lib/needs-you";
import { choices } from "@/lib/choices";
import { gradeSpan } from "@/lib/queries";

export const dynamic = "force-dynamic";

// Every route in this group is behind the staff gate. Actions check again on their own. The menu carries, on every
// page, the count of what waits in each tab: Today's own list (goals/ui1-menu-and-today.yaml); above every page, the bar
// that chooses the subject and the class and searches (goals/s1-subject-class-and-today.yaml).
export default async function AppLayout({ children }: LayoutProps<"/">) {
  const me = await requireStaff();
  const [lines, span, offered] = await deadline(Promise.all([needsYou(me), gradeSpan(), choices()]));
  return (
    <Shell me={me} waiting={counts(lines)} grades={span} choices={offered}>
      {children}
    </Shell>
  );
}
