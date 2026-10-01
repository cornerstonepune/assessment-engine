import type postgres from "postgres";
import { TENANT_SLUG } from "./db";

/** An error a page raised, by the page's pattern, for the live watcher (goals/p2-live-is-watched.yaml). No message: it
 *  can carry a child's name, and Vercel's own log keeps it, found by the digest. */
export async function recordError(sql: postgres.Sql, route: string, kind: string, digest: string | null): Promise<void> {
  await sql`
    insert into web_error (tenant_id, route, kind, digest)
    select id, ${route}, ${kind}, ${digest} from tenant where slug = ${TENANT_SLUG}`;
}
