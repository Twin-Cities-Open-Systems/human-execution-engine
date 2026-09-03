# HEE, Explained Like You Are 5 (Or New)

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

## The core shape

```sh
# idea footgun dogfood - rinse, repeat
# (rinse) <-> idea -> (one way) footgun <-> dogfood -> (repeat)
<-idea->footgun<->dogfood->
```

**That notation is the definition.** Written out as a flat list it loses
the part that matters, so it is reproduced here exactly as Spencer states
it, and every other description in this repo should defer to it.

Read the arrows:

- `(rinse) <-> idea` -- the outer left arrow is two-way. Rinse and idea
  feed each other.
- `idea -> footgun` -- **ONE WAY.** Once an idea is under examination you
  do not walk it back to being an idea; you carry it forward or you drop
  it. This is the only one-way arrow in the shape, which is exactly why it
  is annotated.
- `footgun <-> dogfood` -- these CYCLE. Dogfooding surfaces a footgun;
  fixing it sends you back to dogfood; repeat until dogfooding stops
  producing footguns.
- `dogfood -> (repeat)` -- it flows out the far side and comes round again.

A funnel would be all one-way arrows. This has exactly one.

### This is prior to the tool maturity ladder, and is what makes it work

Spencer, 2026-09-02: *"that is core, even before snfn->sh->bash->py->go, it
is what makes that flow work."*

The ladder (`*.shfn.bash` -> sh/bash -> Python -> a real `hee` subcommand
-> Go/Rust/C, rule 13) says a tool graduates only when it has **actually**
outgrown its rung, on evidence rather than taste. The Graduation Signals
say the same thing and list what the evidence looks like: a regex ceiling,
quoting as the dominant bug source, real parsing needed.

But naming the signals does not produce them. `footgun<->dogfood` does.
Every one of those signals is a footgun found by dogfooding something at
its current rung -- which is why the glossary can say each was "hit for
real, 2026-08-31" rather than reasoned about in advance.

Take the cycle away and "graduate on evidence" has no source of evidence,
so it quietly becomes "graduate when it feels heavy enough" -- the exact
taste-based decision the ladder exists to prevent. The ladder is downstream
of the cycle. It is a consequence, not a peer.

The three stages, spelled out:

1. **Idea** -- propose it, in draft form. Not built, not binding.
2. **Footgun** -- name what could actually go wrong with it, honestly,
   before anyone commits to it.
3. **Dogfood** -- prove it works with real usage, real data, real output.
   Only *then* does it get promoted/ratified into something people rely on.

Take any leg away and it falls over. But a numbered list reads as a
one-way pipeline, and it is not one -- the arrows above are why. An earlier
pass through this material flattened `footgun<->dogfood` into `footgun ->
dogfood` and lost exactly that.

This is the same as the real `propose -> prove -> ratify` sequence already
established in `fleet-ops#16` -- this is just the version you can say out
loud without looking anything up.

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
