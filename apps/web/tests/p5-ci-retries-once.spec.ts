/**
 * A browser test that fails is run once more in CI and not at all on a laptop (docs/adr/0094): a one-off failure that
 * is not the product's no longer holds the release, and one that fails twice still does. No page is opened here.
 */
import { expect, test } from "@playwright/test";
import config from "../playwright.config";
import { retriesFor } from "./retries";

test("CI runs a failed test once more; a laptop does not", () => {
  expect(retriesFor("true")).toBe(1);
  expect(retriesFor("1")).toBe(1);
  expect(retriesFor(undefined)).toBe(0);
  expect(retriesFor("")).toBe(0);
});

test("the config uses it: the retries this run was given are the ones CI mode names", () => {
  expect(config.retries).toBe(retriesFor(process.env.CI));
});
