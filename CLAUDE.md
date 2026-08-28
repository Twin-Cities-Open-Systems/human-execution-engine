# human-execution-engine (HEE)

This repo is the platform-independent doctrine root for the whole TCOS
org -- not GitHub config (contrast `.github`, whose whole job *is*
GitHub-org administration).

@prompts/PROMPTING_RULES.md

That import is the compact, every-session agent rulebook -- every rule in
it traces to either a real dated incident or a mechanically enforced
check. For the detailed "why" behind any of its rules, or anything it
doesn't cover, see `docs/doctrine/HEE_POLICY.md` (the full policy) and
`docs/DOCUMENTATION_POLICY.md` (doc-type taxonomy) -- read on demand, not
every session. Session start itself is gated by `ci/git/hee-preflight.sh`
per `prompts/INIT.md`, which is the real canonical entry point.
