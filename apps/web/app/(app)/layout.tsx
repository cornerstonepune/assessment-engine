import { requireStaff } from "@/lib/auth";
import { Shell } from "@/components/shell";
import { deadline } from "@/lib/deadline";
import { tasksFor } from "@/lib/queries-todo";
import { filterTasks, waitingCount } from "@/lib/todo";
import { subjectsFor, viewSubject } from "@/lib/viewing";
import { choices } from "@/lib/choices";
import { gradeSpan } from "@/lib/queries";

export const dynamic = "force-dynamic";

// Every route in this group is behind the staff gate. Actions check again on their own. The menu carries, on every
// page, the count of what waits in each tab: Today's own list (goals/ui1-menu-and-today.yaml); above every page, the bar
// that chooses the subject and the class and searches (goals/s1-subject-class-and-today.yaml).
export default async function AppLayout({ children }: LayoutProps<"/">) {
  const me = await requireStaff();
  const [tasks, span, offered] = await deadline(Promise.all([tasksFor(me), gradeSpan(), choices()]));
  const mine = subjectsFor(me, offered.subjects);
  return (
    <Shell me={me} waiting={waitingCount(filterTasks(tasks, { subject: viewSubject(me, mine) }, mine.map((s) => s.code)))} grades={span} choices={offered}>
      {children}
    </Shell>
  );
}
