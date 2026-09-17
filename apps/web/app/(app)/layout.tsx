import { requireStaff } from "@/lib/auth";
import { Shell } from "@/components/shell";

export const dynamic = "force-dynamic";

// Every route in this group is behind the staff gate. Actions check again on their own.
export default async function AppLayout({ children }: LayoutProps<"/">) {
  const me = await requireStaff();
  return <Shell me={me}>{children}</Shell>;
}
