// The type check proves the website's engine client holds it to the engine's own routes (goals/p1-types-hold.yaml):
// each call below must not compile, and `@ts-expect-error` fails `tsc` the day one of them does. Never run.
import { engineGet, engineImage, engineSend } from "@/lib/engine";

export async function neverCalled(): Promise<void> {
  // @ts-expect-error a route the engine does not serve
  await engineGet("/no/such/route");
  // @ts-expect-error a picture from a route the engine does not serve
  await engineImage(`/sheet/${"CS000000"}/picture.png`);
  // @ts-expect-error a GET route sent a body
  await engineSend("/bank/proposals", {});
  // @ts-expect-error a body without a field the route needs
  await engineSend("/week/approve", { section: "G3", week: "T2W1" });
  // @ts-expect-error a field the route does not take
  await engineSend(`/bank/item/${"k"}/remove`, { by: "e2e", note: "", why: "" });
  // @ts-expect-error a value the route refuses
  await engineSend(`/bank/proposal/${"id"}/decide`, { verdict: "maybe", by: "e2e" });
}
