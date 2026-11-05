"use client";

import { usePathname } from "next/navigation";
import Link from "./link";
import { guideFor } from "@/lib/guide-path";

// The "?" on a page's header (goals/guide_for_educators.yaml): it opens the Guide's page for the menu item this page
// belongs to. One block, in PageShell, so no page carries it by hand; the guide's own pages have none.
export function HelpLink() {
  const href = guideFor(usePathname());
  if (!href) return null;
  return (
    <Link href={href} aria-label="How this page works, in the guide" title="How this page works" data-ux="help" className="inline-flex h-8 min-w-8 items-center justify-center rounded-full border border-basalt/30 text-[14px] font-medium no-underline hover:bg-basalt/5">
      ?
    </Link>
  );
}
