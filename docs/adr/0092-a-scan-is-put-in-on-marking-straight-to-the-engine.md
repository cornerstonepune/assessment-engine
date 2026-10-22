# 0092 — A scan is put in on Marking, sent by the browser straight to the engine (replaces "Drive folder v1" for N8)

Date: 2026-10-21
Status: proposed
Goal: goals/n8-upload-on-marking.yaml

## Context

The workflow agreed with the school (`docs/sources/assessment-workflow-v1.md`, N8 Capture) named the way photos come
back as "Drive folder v1 / WhatsApp v2". What was built: an educator pastes a Drive link on Marking; the engine fetches
the file into its inbox (`inbox.fetch`) and reads it in the background (`inbox.read`). The file had to be uploaded to
Drive, shared "anyone with the link", and the link copied: three steps an educator gets wrong.

Nimish, 2026-10-21: *"Teachers can directly just put in the assessments, like the PDF copy or scanned copy of the
assessments, there. Then the analysis can happen, and there it says we have a proper understanding of how many questions
have been evaluated, how many questions need validation from the teacher."* He decided this replaces the Drive folder
for N8. The workflow wins over this repository's other documents, so the decision is his, recorded here; the Drive link
stays as a second way in for now, and the n8n Drive-folder flow is not removed by this change.

This is W3 work while W1 gate 3 (B0–B4) is open, by Nimish's own instruction the same day.

## Decision

1. **On Marking (and Papers, which shares the panel), an educator chooses or drops files**: a PDF, or phone photos
   (JPG, PNG, HEIC). Each PDF is sent on its own; every photo chosen together is one paper, made one PDF in the order of
   the photos' names, which is the order a phone took them. Each file shows how much of it has gone.
2. **The browser sends the file straight to the engine**, `POST /read/upload` on the engine's public address (Caddy).
   Vercel's limit, checked in its docs on 2026-10-21 (vercel.com/docs/functions/limitations, "Request body size"):
   *"The maximum payload size for the request body or the response body of a Vercel Function is 4.5 MB."* A class's
   scan is 10–60 MB, so anything through a Vercel function is out.
3. **Auth: a token the site signs, never the engine's key.** When a batch starts, a server action (`scanTicket`, only
   for someone who may put papers in) returns the engine's address and a token: `<email>.<expiry>.<HMAC-SHA256 of
   "upload." + both, keyed by ENGINE_KEY>`, living 30 minutes. The engine (`deps.require_upload_token`) checks the
   signature and refuses a token expired or living over an hour. It opens only that one route; it is not a key.
4. **The engine checks size and kind itself** (`inbox.take`), by the file's first bytes, never its name: 64 MB at most
   (refused before the body is taken in when the request says it is larger), a PDF or a photo, a PDF alone. Each refusal
   is a sentence the page shows. One file refused does not stop the next: each is its own request.
5. **The same reading starts**: the file is saved in the inbox and read in the background exactly as a Drive link's
   (`inbox.start`, `inbox.read`). The run now carries its pages from the start, and each copy its pages on which no code
   could be read (`no_code`), said on the page by number. Marking shows, per file: pages, copies, children, copies read,
   answers, and of them how many the engine settled and how many wait for a person (`answer_standing`), refreshed while
   it reads.
6. **CORS**: the engine answers any origin for `POST` with the `X-Upload-Token` header. Safe because no engine route
   trusts a cookie or an address: each asks for the engine's key or a token only the site can sign.

Scans never enter git, the database or a log (rule 6): the file is written to the inbox on the engine's disk, as a
Drive link's file already was.

## Rejected

- **Through a Next.js route or server action**: Vercel's 4.5 MB body limit; a class's scan is ten times that.
- **A signed upload URL to storage (Supabase Storage, Vercel Blob, S3), which the engine then reads**: handles any size,
  but adds a store, its credentials and bucket policy, a second copy of every child's paper outside the school's
  server, and a hand-over (the engine told the object is there, then fetching it). The engine already has a public door
  and an inbox on its own disk; sending the file there is one request and no new service.
- **The browser holding `ENGINE_KEY`**: it opens every route, forever.
- **Chunked or resumable upload (tus)**: 60 MB in one request is within what Caddy and uvicorn take (neither caps a body
  by default); a dropped upload is sent again. Worth it only if educators report failed uploads on the school's line.
- **Making the PDF from photos in the browser**: HEIC does not decode in most browsers; the engine already holds the
  image libraries (Pillow, with `pillow-heif` added for HEIC) and turns each photo upright by its EXIF.

## Consequences

- Two dependencies are named in the engine: `python-multipart` (FastAPI's form parser, previously present only by
  chance) and `pillow-heif` (HEIC). `pillow` is named too, now imported directly.
- The site needs `ENGINE_URL` to be the engine's public address (it is: `deploy/go-live.sh` sets it to the Caddy host).
- A photographed page whose code cannot be read is reported by its page number. After a whole copy it is a copy of its
  own and not read; inside a copy still short of pages, `sorting.group` already takes it for that copy's next page (a
  sheet's later pages carry the same code, so a missing one is a bad scan). That rule is unchanged here, and the page is
  still named, so a person sees it.
