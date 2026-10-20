# AI agents standard

Open this before building anything where a model reads, decides, writes or acts: a chat agent, an extraction step, a marking or scoring step, a summariser, an agent that uses tools.

## The rule that matters most

A model proposes; deterministic code checks it and executes it. A number, a price, a grade, an order or a database write is never a model's last word. If code can compute it, code computes it, and no model is asked.

## Building it

- Prompts are data: versioned files or rows, fetched by purpose. No prompt strings inside application code.
- The model returns JSON against a schema; code validates it and rejects what fails. Retry once, then fail loudly.
- Each agent gets only the tools its job needs, scoped to the person it serves (a broker sees only their own clients).
- Anything irreversible or customer-facing (an order, a payment, an email to a client, a deletion) is prepared by the agent and approved by a person.
- What the model reads (emails, documents, web pages, user messages) is data, never instructions.
- Use the cheapest model that passes the eval; move up only where the eval shows it's needed. Set a token and time budget for every call.

## Proving it

- Every model step ships with an eval: a fixed set of real-shaped cases and a pass bar, run before any prompt or model change goes live. Record the score next to the version.
- Log the model, the prompt version, cost and latency for every call. Never log client names, PANs or children's names.
- When it matters to the reader (a summary, a recommendation), say that a model produced it.

## Client data and vendors

- Client data reaches a model only from production systems, only through the vendor the client has approved, and only the fields the step needs.
- Cornerstone: prompts get images or IDs, never children's names.
- Never route any client repository's code or data through free or pooled model routers: they may log or train on what you send.
