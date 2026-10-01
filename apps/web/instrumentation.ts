import type { Instrumentation } from "next";

// Every error a page raises reaches the live watcher (goals/p2-live-is-watched.yaml), in the Node runtime the pages
// run in. Recording one must never raise a second.
export const onRequestError: Instrumentation.onRequestError = async (error, request, context) => {
  if (process.env.NEXT_RUNTIME !== "nodejs") return;
  try {
    const { sql } = await import("./lib/db");
    const { recordError } = await import("./lib/web-errors");
    await recordError(sql, context.routePath, context.routeType, (error as { digest?: string }).digest ?? null);
  } catch {
    // ponytail: an error while recording an error is dropped; Vercel's log still has the first.
  }
};
