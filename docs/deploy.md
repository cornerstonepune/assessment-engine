# Deploying the app

The engine is a command line tool a person runs; only the web app is deployed. It is hosted on
Vercel, in Mumbai (`bom1`), next to the database in `ap-south-1`.

## Before the first deploy

Two things must be true, and neither can be done from a script.

1. **The database password has been rotated.** The current one was typed into a chat window, so it
   is not a secret any more. Supabase → Settings → Database → Reset database password, alphanumeric
   only, then update `.env` locally and the Vercel variable below.
2. **Someone is logged in to Vercel**: `vercel login`, then `vercel link` from the repository root.

## Environment variables

Set these in Vercel → Project → Settings → Environment Variables, for Production and Preview.
Their values are in the repository's `.env`, which is never committed.

| Variable | Where it comes from | Why |
|---|---|---|
| `DATABASE_URL` | Supabase → Connect → **Transaction pooler**, port **6543** | Every screen reads Postgres directly. Serverless needs the transaction pooler; the session pooler on 5432 runs out of connections under load. |
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase → Settings → API | Sign-in only |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase → Settings → API, the publishable key | Sign-in only. Never the service-role key: that one bypasses every row-level policy and must never reach a browser. |
| `NEXT_PUBLIC_SITE_URL` | the deployment's own URL | Where a magic link returns to |
| `TENANT_SLUG` | `cornerstone-pune` | Which school's rows |

**`AUTH_DEV_BYPASS` must never be set on Vercel.** It is refused outside development, but an
unset variable cannot be misread.

## Supabase, once

Authentication → URL Configuration → Redirect URLs: add `https://<the deployment>/auth/callback`.
A magic link to a URL that is not on that list silently fails. Already done for the current URL.

### Check the key is a key

`SUPABASE_ANON_KEY` sat in `.env` as a nine-character placeholder that nobody had filled in, and the
only symptom was "the link could not be sent" on a screen that otherwise looked perfectly healthy.
Before blaming email, confirm the key actually authenticates:

```bash
curl -s -o /dev/null -w '%{http_code}\n' \
  -H "apikey: $SUPABASE_ANON_KEY" "$SUPABASE_URL/auth/v1/settings"
```

`200` means the key is good; `401` means it is wrong, whatever its shape. Use the **publishable**
key (`sb_publishable_…`), never the secret or service-role one — that reaches the browser.

### Email sending is not production-ready yet

The project has no SMTP server configured, so Supabase sends through its own shared service, which
allows **two emails an hour** and is not intended for real use. Three staff signing in one morning
will exhaust it. Before the pilot widens, connect a real sender (Resend, SendGrid, Postmark, or the
school's own Google Workspace SMTP) under Authentication → Emails → SMTP Settings, and raise
`rate_limit_email_sent` to match.

## Who can sign in

Nobody, until their school email is in the `app.staff` config row. Add them to
`supabase/seed/config.json` and run `engine load`, or update the row directly. Everyone else gets
"that email is not on the staff list" — signing in to Supabase is not the same as being staff.

## Deploy

Deploy **from `apps/web`**, not from the repository root. Vercel decides a project is a Next.js
app by finding `next` in the `package.json` of the directory it is given, and the root one is not
a Node project at all. `apps/web/vercel.json` carries the build settings and the Mumbai region.

```bash
cd apps/web && vercel --prod
```

The Python engine is not built or deployed; it runs where a coordinator runs it.

Live: **https://cornerstone-assessment.vercel.app**

## Never put a connection string together in the shell

A bash substitution to swap the port produced `…:6543\/postgres`, the driver rejected it, and its
error quoted the whole string — **password included — into the build log**. Build a connection
string with a real URL parser, and check its shape before it reaches the driver, which `lib/db.ts`
now does so the message never carries the credentials.

## What is exposed

Every route is behind the staff gate, including the API-shaped ones. No child's name reaches the
app at all: the web app reads roll numbers and never touches the `pii` schema, which only the
engine reads, through an accessor that logs every read.

The one thing worth saying plainly: `DATABASE_URL` gives the app full access to the database, so
the deployment is only as safe as that variable and the staff list. That is the shape ADR 0001
chose, and it is acceptable for a pilot behind a short allowlist. If the pilot widens beyond the
school's own staff, move the app to the anon key and let row-level policies do the work.
