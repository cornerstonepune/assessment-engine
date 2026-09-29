"use client";
// While the engine writes a report (a background run; writing and reading a draft twice over outlasts the site's
// thirty seconds), the page asks the server again every few seconds, and stops once the run has ended.
import { useRouter } from "next/navigation";
import { useEffect } from "react";

export function Refresh({ everyMs = 5000 }: { everyMs?: number }) {
  const router = useRouter();
  useEffect(() => {
    const t = setInterval(() => router.refresh(), everyMs);
    return () => clearInterval(t);
  }, [router, everyMs]);
  return null;
}
