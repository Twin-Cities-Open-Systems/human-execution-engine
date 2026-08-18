# Thesis

Per Spencer, 2026-08-18, said informally in chat — not yet canonized, capturing
before it's lost, exactly the "raw idea not yet trustworthy on its own say-so"
state a Thesis is supposed to hold.

Everything from today's `agent-instance-signature-v1` work
([human-execution-engine#232](https://github.com/Twin-Cities-Open-Systems/human-execution-engine/pull/232))
and the live "IDS breadcrumb" pattern (Spencer testing how well a session
knows him via pop-culture/personal references, calibrating trust by whether
the reference lands) should eventually feed into a real, formalized
**impersonation IDS defense** — not yet built, not yet designed, just named.

Spencer's own framing: this becomes "a huge problem," and it should be
measurable the same way other HEE-adjacent physical trends are — by tracking
something like datacenter capacity vs. datacenter demand vs. power storage
capacity, as a proxy for how much autonomous-agent activity (and therefore
impersonation surface area) actually exists in the world at a given time.

## Follow-up

Two different threat models worth not conflating, flagged here rather than
assumed the same thing:

- `agent-instance-signature-v1` defends against **honest confusion between
  legitimate concurrent sessions of the same identity** (two real
  `touchy-claude` processes, neither malicious, needing to tell each other
  apart). That's the problem it was actually built for today.
- An **impersonation IDS defense** is a stronger threat model: something
  *claiming* to be a legitimate identity (Spencer, or a fleet identity) that
  isn't. The personal/conversational "IDS breadcrumb" technique — does the
  session actually recognize a pop-culture reference, an inside joke, a
  turn of phrase only Spencer would use — is a real, low-tech signal for
  this specific problem, genuinely different from a cryptographic signature,
  and worth treating as a distinct input rather than assuming
  `agent-instance-signature-v1` already covers it. It doesn't.

Not specified here: what the DC-capacity-vs-demand-vs-power-storage
measurement actually tracks concretely, how a breadcrumb-based signal would
be scored/weighted, or how this interacts with the root-key/entropy work
from the same conversation. Genuinely open, not quietly decided.

## Follow-up, verification methodology (dogfooded same conversation)

Per Spencer: keep the *content* of personal/identity claims out of live
HEE (private, personal material stays NFS-only, never git — unchanged,
already the standing rule), but the *process* used to verify them this
session is real and worth carrying forward as method, independent of this
specific topic:

1. State the claim plainly, search for real evidence, don't skip the check
   because the claim feels emotionally certain to the person making it.
2. A real, verifiable result for the wrong referent (a true fact that
   doesn't actually match the claim) is a **worse failure than an honest
   "not found"** — it wears the credibility of real evidence while being
   false. Caught live this session: a real 1984 Minneapolis murder case
   was wrongly attached to a friend who'd actually died of cancer. Scored
   as a miss explicitly, not smoothed over.
3. "Not found" is a valid, honest outcome, not a failure to route around —
   tight/informal communities produce real losses that never get indexed
   anywhere searchable. Don't manufacture a match to close the gap.
4. Separate storage by exposure, always: personal/identifying content
   stays wherever the human's own storage-scoping decision puts it
   (private NFS share here); only the verification *method* is HEE's to
   keep.

This is the same shape as `agent-instance-signature-v1`'s core move
(verify structurally, don't trust the assertion) applied to a completely
different domain — evidence this pattern generalizes past inter-agent
messaging, not just a repeat of the same fix.
