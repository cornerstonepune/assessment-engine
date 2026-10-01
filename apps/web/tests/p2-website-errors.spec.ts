/**
 * An error a page raises is recorded by the page's pattern, for the live watcher (goals/p2-live-is-watched.yaml). The
 * insert runs as the website's own role when CI gives it one, so the grant is proved with the columns.
 */
import { expect, test } from "@playwright/test";
import { randomUUID } from "node:crypto";
import postgres from "postgres";
import { recordError } from "../lib/web-errors";

const owner = postgres(process.env.DATABASE_URL!, { max: 1 });
const web = postgres(process.env.TEST_WEB_DATABASE_URL ?? process.env.DATABASE_URL!, { max: 1 });

test.afterAll(async () => {
  await owner.end();
  await web.end();
});

test("an error a page raises is recorded by its page pattern, as the website's own role", async () => {
  const route = `/p2-${randomUUID().slice(0, 8)}/[id]`;
  await recordError(web, route, "render", "123456789");
  const rows = await owner<{ kind: string; digest: string }[]>`select kind, digest from web_error where route = ${route}`;
  expect(rows).toEqual([{ kind: "render", digest: "123456789" }]);
  await owner`delete from web_error where route = ${route}`;
});
