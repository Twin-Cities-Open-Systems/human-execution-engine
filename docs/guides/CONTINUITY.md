# Continuity: what happens when Claude runs out of budget

Real constraint, not hypothetical: on 2026-08-24 the primary working session
hit ~90% of the weekly Anthropic usage. Fallback tiers, honestly marked --
**proven** (used for real that night), **designed, untested**, or **not yet
built**:

1. **Another Claude session/peer picks up the work -- proven.**
   [`prompts/INIT.md`](prompts/INIT.md) is the canonical bootstrap entry
   point: point any Claude session at it and it re-derives full context
   (shift-init ceremony, pill index, governing contracts). Used live
   on 2026-08-24 across 3 concurrent sessions. **Real limit**: usage budget is
   almost certainly shared at the account/subscription level, not
   per-session -- this tier buys parallelism, not more total budget.
2. **A local model for narrow binary-predicate gates -- designed, not yet
   built.** [`hee/docs/local-llm-architecture.md`](hee/docs/local-llm-architecture.md)
   (thesis) + [HEE#352](https://github.com/Twin-Cities-Open-Systems/human-execution-engine/issues/352)
   (tracking issue). Scope is deliberately narrow: a sub-4B quantized model
   answering a yes/no gate in <100ms, *not* a Claude replacement for real
   reasoning/agentic work. Infra check 2026-08-24: 8 LXCs, ~15GB RAM free. Re-measured 2026-09-06:
   13 running, ~11GB free -- capacity still exists, nothing deployed yet. No `ollama`/`llama.cpp`/equivalent installed anywhere in the fleet
   (re-checked on kiosk 2026-09-06: still none).
3. **A different vendor's agentic coding CLI as a full drop-in -- designed
   in theory, never actually tested.** `INIT.md`'s doctrine-first design is
   meant to be model-agnostic ("point any agent, from anywhere, at this
   file"), but this has only ever been exercised by Claude sessions. No
   non-Claude agentic CLI (Gemini CLI, Aider, Cursor Agent, etc.) is
   installed anywhere in the fleet, and the claim that a different model
   could actually pick up HEE work cold has **not been verified**. Real
   gap, not yet closed -- don't assume this tier works until it's actually
   been run once.
4. **A second Anthropic account/API key for urgent-only work -- available,
   not automated.** Bridges the narrowest, most time-sensitive items only;
   real cost/ops tradeoff (separate billing), not a scale solution.

Tiers 2 and 3 are the real, open work: HEE#352 covers tier 2's build; tier
3 has no tracking issue yet and needs one before it's more than an idea.
