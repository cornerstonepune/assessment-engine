# ADR 0093 — Staff sign in with their school Google account, and only with it

**Status:** accepted (2026-10-22). Supersedes the password half of ADR 0069.
Goal: goals/a1-sign-in-with-google.yaml

## What happened

Nimish, 2026-10-22: "the default, irrespective of anything, should be the Cornerstone email ID, so no one can log in
without the Cornerstone email ID … sign in using gmail … right now, we just put me as the admin and everyone else as
the educator … no one outside of the school is going to have access." The school is on Google Workspace,
cornerstoneschool.in.

## Decision

- Google OpenID Connect, authorization code flow with PKCE and state, by **arctic** (its generic `OAuth2Client`): small,
  three dependencies, endpoints passed per call, so the browser tests can stand a fake Google on the machine. The ID
  token is checked by **jose** against Google's published keys: signature (RS256 only), issuer, audience, expiry.
- Let in only `email_verified === true`, an email ending `@<domain>`, and `hd === <domain>`. The `hd` sent to Google
  only picks the account; the server's check is the gate.
- The domain and the role a first sign-in gets are a row, `config.app.sign_in`. A school email new to `app.staff` joins
  it as that role, in one statement; someone already on it keeps their role, name and classes. The coordinator is put
  on the list by `engine staff add --role coordinator` before their first sign-in.
- The session cookie, `proxy.ts` and `requireStaff` are unchanged. The password form, its checks, the wrong-password
  limit and `engine set-password` are gone; browser tests other than the sign-in's start from a signed cookie.

## Rejected

- **openid-client.** Certified and thorough, but it discovers its endpoints from the issuer, so a fake Google for the
  tests needs a fake issuer and insecure-request flags: more configuration than the flow it saves.
- **Hand-written OAuth.** The state, PKCE and token exchange are where sign-in bugs live; adopted, not written.
- **The admin's address in the seed or in code.** The repository is public (ADR 0069): an address there is published.
- **Keeping the password as a fallback.** It is the door Nimish asked to close; a test-only door into a production
  build would be one more to guard.

## Left as it is

`sign_in_failure` and the `sign_in.*` thresholds are read by nothing now. Dropping them is a migration on live
(rehearsed first), so it is its own step, not this one. Staff names stay in `app.staff`, where they already were; they
are not children's names, which rule 6 keeps in `pii`.
