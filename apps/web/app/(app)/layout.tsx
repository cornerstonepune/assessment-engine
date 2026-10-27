import { requireStaff } from "@/lib/auth";
import { Shell } from "@/components/shell";
import { deadline } from "@/lib/deadline";
import { tasksFor } from "@/lib/queries-todo";
import { filterTasks, waitingCount } from "@/lib/todo";
import { subjectsFor } from "@/lib/viewing";
import { choices } from "@/lib/choices";
import { gradeSpan } from "@/lib/queries";

export const dynamic = "force-dynamic";

// Every route in this group is behind the staff gate. Actions check again on their own. The menu carries, on every
// page, the count of what waits: What needs doing's own list, in the person's subjects and classes, the same figure the page shows.
export default async function AppLayout({ children }: LayoutProps<"/">) {
  const me = await requireStaff();
  const [tasks, span, offered] = await deadline(Promise.all([tasksFor(me), gradeSpan(), choices()]));
  const mine = subjectsFor(me, offered.subjects);
  return (
    <Shell me={me} waiting={waitingCount(filterTasks(tasks, {}, mine.map((s) => s.code)))} grades={span}>
      {children}
    </Shell>
  );
}
