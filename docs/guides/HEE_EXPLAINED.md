# HEE, Explained Like You're 5 (Or New)

## What this document is, and isn't

This is a **teaching document**, not a formal one. Everything in it is a
real, honest simplification of something more precisely stated elsewhere
(mostly `docs/HEE.md` and `docs/doctrine/DECISION_FRAMEWORK.md`).
Its job is to make a newcomer *get it* fast — over coffee, in a hallway,
to a new human OPER on day one — not to survive a formal-logic audit.

If something here ever conflicts with the doctrine it's simplifying, the
doctrine wins. This file gets updated to match, not the other way around.

Why this exists as its own thing, separate from the doctrine: HEE is
philosophically deep at its core (see `HEE#262`, the real, ongoing work
quantizing Proudhon/Marx/Bakunin/Kropotkin into `hee-ratios(tm)`), and
most people don't get that on first contact. Precise language is correct
for governance. It's bad for a first fifteen minutes.

## The core shape: idea -> footgun <-> dogfood

Every real thing in HEE goes through the same three-legged stool before
it's trusted. Take any leg away and it falls over.

1. **Idea** -- propose it, in draft form. Not built, not binding.
2. **Footgun** -- name what could actually go wrong with it, honestly,
   before anyone commits to it.
3. **Dogfood** -- prove it works with real usage, real data, real output.
   Only *then* does it get promoted/ratified into something people rely on.

This is the same as the real `propose -> prove <-> ratify` sequence already
established in `fleet-ops#16` -- this is just the version you can say out
loud without looking anything up. Notice that ideas move to footguns, and
dogfood can send back to dogfood - but never correct the idea. This is key
to understanding hee philosphy.

## The illustrative "axioms"

These are teaching shorthand, not formal doctrine -- each one is a real
simplification of something precisely stated elsewhere, shown here with
the real thing that proved it true.

### "The human is the runtime, not the rubber stamp."

The real, precise version: HEE.md's own Normative Property #1 -- the
human is "not a passive assignee... not an approval gate... the execution
runtime itself."

**Real footgun this catches:** treat a human's approval as a checkbox and
you get exactly what happened this session -- an approved PR got merged
by the approver, which turned out to be the wrong party to do it, because
"approve" and "execute" got silently treated as the same act. They aren't.

### "Nothing is real until it's dogfooded."

**Real proof, this session:** every tool shipped tonight was run against
real data before being trusted -- `hee-sqz` against the real 15-repo
branch-protection rollout, `hee-git-merge`'s new dependency ordering
against the real `HEE#279`->`#298` case (computed order matched a manual
one exactly, from real diff content, not a guess).

### "Verify, don't vibe."

**Real footgun this catches:** `reviewDecision: APPROVED` looked like
"safe to merge." On two real repos this session it wasn't -- their
`dismiss_stale_reviews` setting was off, so an approval could keep
showing as current after new commits landed. Trusting the label instead
of the underlying state would have merged something nobody actually
re-reviewed.

### "Fewest new things, most real content."

**Real proof, this session:** a request for a "mass approve tool" became
one new flag on an existing tool, not a new one. A request for a
"git-scrub policy" turned into codifying a real, already-executed 2026-08-15
incident, not inventing a new procedure. A proposal for a formal "HEE
axioms document" got turned down in the same conversation this file comes
from -- because the category was empty, and creating a home for nothing
yet is the same mistake as creating five contracts for a chain that only
needs two.

## How to use this with a new human OPER

Don't hand someone `HEE_POLICY.md` on day one. Hand them this. When they
ask "why," point at the real doctrine file the simplification came from --
the stool has three legs for a reason, and "because it's real, go look"
is a better answer than "because the rules say so."

## See also

- `docs/HEE.md` -- the real, formal definition this simplifies
- `docs/doctrine/DECISION_FRAMEWORK.md` -- the real decision logic these
  illustrations point back to
- `fleet-ops#16` -- the real propose/prove/ratify precedent behind the
  stool
- `HEE#262` -- the real philosophical lineage work this document exists
  to make approachable, not to replace
