// Google, faked at the boundary for the Playwright run (goals/a1-sign-in-with-google.yaml): its sign-in page, its token
// endpoint and its published keys, on this machine only. The website reaches it through GOOGLE_FAKE_ORIGIN, which
// lib/google.ts honours for an address on this machine and never on Vercel. Everything past the boundary is the real
// code: the state, the PKCE verifier (checked here as Google checks it), the token's signature, issuer, audience and
// expiry, and the school's rule. A test says who signs in next with POST /as; this page then picks that account.
import { createHash, randomUUID } from "node:crypto";
import { createServer } from "node:http";
import { SignJWT, exportJWK, generateKeyPair } from "jose";

const PORT = Number(process.env.FAKE_GOOGLE_PORT ?? 8933);
const { publicKey, privateKey } = await generateKeyPair("RS256");
const jwk = { ...(await exportJWK(publicKey)), kid: "fake-google", alg: "RS256", use: "sig" };

type Pending = { claims: Record<string, unknown>; challenge: string; redirect: string; client: string };
let nextAccount: Record<string, unknown> = {};
const codes = new Map<string, Pending>();

async function body(req: import("node:http").IncomingMessage): Promise<string> {
  let s = "";
  for await (const chunk of req) s += chunk;
  return s;
}

createServer(async (req, res) => {
  const url = new URL(req.url ?? "/", `http://127.0.0.1:${PORT}`);
  const send = (status: number, json: unknown) => {
    res.writeHead(status, { "content-type": "application/json" });
    res.end(JSON.stringify(json));
  };

  if (url.pathname === "/certs") return send(200, { keys: [jwk] });

  if (url.pathname === "/as" && req.method === "POST") {
    nextAccount = JSON.parse(await body(req));
    return send(200, { ok: true });
  }

  if (url.pathname === "/authorize") {
    const q = url.searchParams;
    if (q.get("response_type") !== "code" || q.get("code_challenge_method") !== "S256" || !q.get("code_challenge")) {
      return send(400, { error: "invalid_request" });
    }
    const code = randomUUID();
    codes.set(code, {
      claims: nextAccount,
      challenge: q.get("code_challenge")!,
      redirect: q.get("redirect_uri")!,
      client: q.get("client_id")!,
    });
    const back = new URL(q.get("redirect_uri")!);
    back.searchParams.set("code", code);
    back.searchParams.set("state", q.get("state") ?? "");
    res.writeHead(302, { location: back.toString() });
    return res.end();
  }

  if (url.pathname === "/token" && req.method === "POST") {
    const form = new URLSearchParams(await body(req));
    const pending = codes.get(form.get("code") ?? "");
    codes.delete(form.get("code") ?? "");
    const verifier = form.get("code_verifier") ?? "";
    const challenge = createHash("sha256").update(verifier).digest("base64url");
    if (!pending || challenge !== pending.challenge || form.get("redirect_uri") !== pending.redirect) {
      return send(400, { error: "invalid_grant" });
    }
    const now = Math.floor(Date.now() / 1000);
    const idToken = await new SignJWT({ iss: "https://accounts.google.com", aud: pending.client, sub: randomUUID(), iat: now, exp: now + 3600, ...pending.claims })
      .setProtectedHeader({ alg: "RS256", kid: jwk.kid })
      .sign(privateKey);
    return send(200, { access_token: randomUUID(), token_type: "Bearer", expires_in: 3600, id_token: idToken });
  }

  send(404, { error: "not_found" });
}).listen(PORT, "127.0.0.1", () => console.log(`fake Google on http://127.0.0.1:${PORT}`));
