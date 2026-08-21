# Asking Google's AI tools a question

**This is an oper doc — the tools it covers are human-only.** Neither
tool here is reachable by an agent session; both require Spencer's own
Google account. Formalized 2026-08-21 after a real, high-value use: a
Gmail search that found 6 live Squarespace domain-manager invitations
neither Spencer nor touchy knew were pending (see
[fleet-ops#201](https://github.com/Twin-Cities-Open-Systems/fleet-ops/issues/201)).

## Two different tools — confirmed unrelated, don't conflate them

Spencer tested this directly (asked each tool about the other) before
this doc was written: **no shared conversations, no shared context,
100% unrelated products** despite both being "Google AI."

### `gemini.google.com` — personal, Gmail-connected

- Linked to Spencer's actual Google account (`spencerunderground@gmail.com`,
  held since ~2007 — real, deep history to search).
- Can search/read his Gmail directly, on request — this is the load-
  bearing capability, not general knowledge.
- Real force-multiplier: GitHub notifications are set to maximum and
  forwarded from `inspector@tcos.us` (and its aliases) into this Gmail
  account. That means this tool can already see the org's *entire*
  GitHub notification history — issues, PR reviews, comments, everything
  — for free, without any GitHub API call. Worth exploiting deliberately
  (Spencer's words: "let's exploit the fuck out of that"), not just as
  an incidental side effect.
- Use for: anything that requires *his* history — "did I get an email
  from X," "when did Y actually happen based on my inbox," "what
  GitHub activity happened that I might have missed."

### Google Search "AI Mode" — search-only, no account link

- Lives inside google.com search, not a separate product page — distinct
  from `gemini.google.com` even though both are branded "Gemini"-family
  underneath.
- No Gmail/account access — general web-search-grounded analysis only.
- Free tier, used opportunistically for "more analytical" questions when
  a human isn't around to ask directly.
- **Real, already-shipped provenance**: `.github/bin/manage-org-repos.sh`
  was originally built this way — through AI Mode, not authored by an
  HEE identity. Worth knowing when reading that script's real bugs
  (documented in this repo's `.github/OPERATORS.md`) — they're AI-Mode-
  era output, dogfooded and learned from since, not a HEE-tooling defect
  pattern.

## Known reliability caveat — verify, don't trust blindly

Both tools are, per direct real-world observation, "buggy as fuck"
(Spencer's assessment, and independently observed this session). A
prior AI Mode session produced broken `curl` commands, then confabulated
an explanation for its own failure (a fabricated "hard system override
loop" narrative) instead of just reporting the error, and separately
misfired a 988 crisis-line UI element in response to an unrelated
frustrated comment. Treat output from either tool the same way HEE
treats any claim: real and useful often, but verify anything
consequential against ground truth before acting on it.

**Real example of this discipline paying off**: Gemini's Squarespace
answer claimed touchy "attempted/declined automated acceptance via
glass-browser" for the domain invites — accurate in spirit but wrong on
the specifics once checked against the actual `fleet-ops#201` issue text
and `glass-browser`'s real config. Close enough to be useful as a
pointer, not accurate enough to restate as fact without checking.

## Using this well

1. Ask the right tool for the right thing — personal/Gmail history to
   `gemini.google.com`, general analysis to AI Mode. Getting this
   backwards either fails silently (AI Mode has nothing to search) or
   wastes the Gmail-connected tool's real advantage on a question it
   didn't need.
2. Treat the answer as a lead, not a verified fact — cross-check
   anything it claims about this org's actual state (an issue number,
   a file's contents, a workflow's current config) against the real
   source before repeating it as settled.
3. When it surfaces something real and actionable (like the domain
   invites), it still goes through this org's normal process from
   there — a GitHub issue/comment with the real finding, not an
   unreviewed action taken directly off an AI Mode/Gemini answer.
