# Can we generate questions on GLM 5.2 or Kimi K2.6?

Researched 2026-09-18. **Recommendation: try GLM 5.2 for question generation, behind the existing
adapter, and decide on measured numbers. Do not use either for reading children's work.**

## Why this is even worth asking

Question generation is the most cost-sensitive job in the system and, unusually, the most forgiving
of a weaker model — because `assess/verify.py` recomputes every number before an item exists. A
cheaper model cannot put a wrong answer on a child's paper. If it is worse, the only symptom is a
lower acceptance rate: more requests for the same number of questions. That makes this a safe
experiment in a way it would not be almost anywhere else in the system.

## Prices, per million tokens

| | Input | Output | Context | Source |
|---|---|---|---|---|
| Claude Opus 5 | $5.00 | $25.00 | 1M | first-party |
| Claude Sonnet 5 | $2.00 | $10.00 | 1M | first-party |
| **GLM 5.2** | **$1.40** | **$4.40** | 1M | Z.ai official; $0.26 cached input |
| **Kimi K2.6** | **$0.95** | **$4.00** | 262K | Moonshot official; batch is 40 % off |
| GLM 5.2 via OpenRouter | $0.49 | $1.53 | | third-party reseller |
| Kimi K2.6 via OpenRouter | $0.37 | $1.58 | | third-party reseller |

Against Sonnet 5, GLM 5.2 is roughly **2.3× cheaper on output**, which is where nearly all the
money goes: a 20-question request measured on this system spends about 17,000 of its 19,800 tokens
on the model reasoning through the arithmetic.

## Quality, on the axis that matters here

Artificial Analysis has GLM 5.2 ahead of Kimi K2.6 overall (intelligence index 34 vs 27) and
markedly ahead on the reasoning benchmarks closest to our task — CritPt physics reasoning 21 % vs
8 %, Humanity's Last Exam 41 % vs 37 %. Kimi wins on long-context recall, which we do not need: our
prompt is about 800 tokens.

Neither published figure tells us the thing we actually care about, which is **what fraction of
generated items survive our verifier**. That is measurable in an afternoon and is the only number
that should decide this.

## Privacy — the decisive split

**Generating questions sends no child data at all.** The prompt is a skill description: an
operation, digit counts, a difficulty rule in words, and a list of misconception names. No child,
no name, no work, nothing a parent could object to. On this job the provider's training policy is
close to irrelevant.

**Reading a child's paper is the opposite**, and the two must not be conflated because one
experiment went well. Moonshot's published policy says prompts and uploaded content may be used to
train its models, with no clear opt-out below enterprise scale — the inverse of the Anthropic and
OpenAI API posture, where API traffic is excluded from training by default. Independent reviews
rate Kimi medium-to-high privacy risk for sensitive data absent a negotiated agreement. I could not
find published zero-retention terms for Z.ai either.

So the rule for this repository: **a cheaper provider may write questions; it may not see a child's
handwriting.** ADR 0004's masking requirement stands, and the vision provider stays a separate
decision.

## What it would cost to try

The engine was built for this. `adapters/llm.py` is 113 lines and the only module that knows a
provider exists; each prompt already carries its own model name in a `prompt` row. Both providers
expose OpenAI-compatible endpoints, so this is roughly 40 lines plus an API key — a
`_call_openai_compatible` alongside the existing `_call`, chosen by the model name's prefix.

## How to decide it, rather than argue about it

1. Add the provider to the adapter; put the model id in the `item_generate` prompt row.
2. `engine eval item_generate` on all four skill sets at all four difficulties.
3. Compare three numbers per model: **acceptance rate**, **tokens per accepted question**, and
   **cost per accepted question**. The last is the one that matters; a cheap model that fails the
   verifier twice as often is not cheap.
4. Have Neha or Achal read twenty word problems from each, blind. The arithmetic is guarded by
   code; the English is not, and a sentence that does not sound like a Pune classroom is the
   failure mode no test will catch.

## Prediction, recorded so it can be checked

Both will handle the arithmetic acceptably, because the verifier catches what they get wrong. The
real risk is the word problems: register, names, and whether the contexts feel local. I expect GLM
5.2 to be the better of the two and to be adequate; I expect the gap to show up in the reading, not
in the numbers.

## Sources

- [GLM 5.2 on OpenRouter](https://openrouter.ai/z-ai/glm-5.2)
- [GLM 5.2 pricing, llm-stats](https://llm-stats.com/models/glm-5.2)
- [Zhipu GLM API pricing 2026](https://aiapiprices.com/zhipu-glm-api-pricing/)
- [Kimi K2.6 on OpenRouter](https://openrouter.ai/moonshotai/kimi-k2.6)
- [Moonshot API pricing, BenchLM](https://benchlm.ai/moonshot/api-pricing)
- [GLM-5.2 vs Kimi K2.6, Artificial Analysis](https://artificialanalysis.ai/models/comparisons/glm-5-2-vs-kimi-k2-6)
- [Kimi OpenPlatform privacy policy](https://platform.kimi.ai/docs/agreement/userprivacy)
- [Kimi safety and privacy analysis, CometAPI](https://www.cometapi.com/is-kimi-safe-to-use/)
- [Kimi AI trust rating, VerifyWise](https://verifywise.ai/ai-trust-index/kimi)
