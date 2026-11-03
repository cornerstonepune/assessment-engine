# K2 voice notes: which tool turns the recording into words (task M1-01, step 1)

W3 (read and graph), a new step N3b "Voice notes" proposed for `workflows.json` (the map changes first, in the
parser's pull request). Fixtures here are an adult reading the template with placeholder numbers: never school
data, never proof (D-056).

## What has to be true of the tool

- Hindi-English classroom speech, numbers above all: "seventeen", "satrah", "one seven" must all come out as words
  the parser can read. The parser, not the tool, turns words into numbers, and the educator confirms every line, so
  the tool has to be good enough to save time. It decides nothing.
- Audio stays on the private side (O-14 is open: keep it, make retention a setting, delete nothing yet).
- It runs on what we have, or the cost of what we'd need is stated.

## Candidates, and what I actually read (3 Nov 2026)

| | faster-whisper (Whisper models), on our own server | Sarvam AI speech-to-text, hosted |
|---|---|---|
| What it is | A re-implementation of OpenAI Whisper on CTranslate2. Models named on its page: `large-v3`, `large-v2`, `turbo`, `distil-large-v3`, `small` | Indian company's API. `POST https://api.sarvam.ai/speech-to-text`, multipart, header `api-subscription-key`; fields `file`, `model` (`saaras:v4` default, or `saaras:v3`), `mode` (v3 only: `transcribe`, `translate`, `verbatim`, `translit`, `codemix`), `language_code` (`hi-IN`, `en-IN`, `unknown`…) |
| Licence | MIT (the library's GitHub page). Whisper weights are published by OpenAI under MIT. **Worth verifying** the weights' licence on the model card before adopting | Commercial service; terms not read. Price on its pricing page: ₹30 per hour of audio, billed per second. **Verify** on sarvam.ai/api-pricing before signing up |
| Where the audio goes | Nowhere: our server | To Sarvam. Its marketing pages say audio is processed and stored in India, not used for training, deleted after processing unless retention is asked for. **I have not read its data-processing agreement**; that, not the marketing page, is what a school's consent register (C6) can rely on |
| Fits our server? | **No, not as it is.** The engine's Lightsail box has 2 GB of RAM (`deploy/go-live.sh` picks the 2 GB bundle). The page reports `small` in int8 on CPU using about 1.5 GB; `large-v3` needs more than the box has. A bigger box or a second one is needed: a cost not yet priced | Nothing to run |
| Hindi-English mixing | Whisper detects one language per recording; I found no measurement of code-mixed classroom speech. **Unknown until measured** | Has a mode named `codemix`. I found no published accuracy for it. **Unknown until measured** |
| A REST call's length | Any | Its page says the REST call is for audio under about 30 seconds; longer goes to its Batch API. A K2 note is meant to be short; this must hold |

Considered and set aside for the spike: AI4Bharat IndicConformer (Hindi model card says MIT, but the download is gated
behind accepting terms, and an older sister model carried CC-BY-4.0: licence needs confirming, and it is Hindi-only, so
English words in a mixed note are its weakness). Kept as a third own-server candidate if Whisper fails on Hindi numbers.

## What I could not do here

- **Measure anything.** This build container has no microphone and no text-to-speech voice, and a machine voice would
  not be an adult in a classroom anyway. No fixture exists yet. No Sarvam key exists here.
- So **no tool is chosen yet.** The decision rule, written before the numbers: on the fixtures, count the numbers the
  parser reads right from each tool's transcript. The own-server tool is chosen if it reads every number right on
  every fixture (rule 12: 100 %); otherwise the hosted one, if it does, with its data terms read first; otherwise
  neither, and the educator types or corrects the note on Confirm. Everything else (parser, tables, screens) is built
  against typed transcripts meanwhile, so the tool is a swap of one adapter file.

## Recording instructions for Nimish (the fixtures, S-M1-01-fixtures)

1. Use any phone's voice recorder. One adult (you, or anyone at the office), in a normal room; a little background
   noise is good. **No children, no real class, no real child's number.** Numbers 1 to 30 are fine as placeholders.
2. Record **8 notes**, each 10 to 30 seconds, each one reading the spoken template (field/k2-shadow-capture.md) with
   made-up numbers. Vary them:
   - 1 and 2: plain English, slowly, then quickly.
   - 3 and 4: the numbers in Hindi ("teen, saat, unnees"), the rest in English.
   - 5: a number said twice ("seven, seven"), and one corrected ("twelve, no, thirteen").
   - 6: a pause and an "umm" in the middle; one list empty ("none below").
   - 7: one free sentence at the end, and the word "incident" with a made-up line.
   - 8: fast, mixed Hindi and English throughout.
3. After each recording, write down exactly what you said (the numbers especially) in a text file of the same name.
4. Name them `fx-01-english-slow.m4a` … `fx-08-mixed-fast.m4a`, with `fx-01-english-slow.txt` beside each.
5. Put them in one folder in Google Drive and share it with the build (not in GitHub: audio never goes in git, and
   `.gitignore` refuses audio files from this pull request on).
