# Human Execution Engine (HEE)

[![CI/CD Pipeline](https://github.com/Twin-Cities-Open-Systems/human-execution-engine/actions/workflows/ci.yaml/badge.svg)](https://github.com/Twin-Cities-Open-Systems/human-execution-engine/actions/workflows/ci.yaml)

HEE is a **doctrine-first execution framework** for coordinating human reasoning, machine assistance, and automation **without ambiguity**.

It prioritizes:

- correctness over consensus,
- structure over vibes,
- determinism over convenience.

This repository is the **canonical source of HEE doctrine**.

---

## Tooling & Workflows

- Patching workflow: `docs/tools/patching.md`
- Operator tools: `tools/oper/README.md`
- Automation tools: `tools/auto/README.md`

## Tooling docs

- Patching workflow: `docs/tools/patching.md`

## Core Principles

- **Doctrine defines correctness.**
- **Operations enforce doctrine.**
- **Instances execute within doctrine.**

Doctrine is **standing, non-terminal**, and validated **strictly**.

---

## Skin in the Game

When TCOS participates in an external network or community as more than
a one-off lookup, it runs real, owned, persistent infrastructure — not
an ephemeral client session borrowed for the moment.

**Real trigger**: deciding how to rejoin `#tclug` on Libera.Chat.
A one-shot read-only probe (join, read the roster, quit) answered "is
anyone there" — real, honest, and correctly scoped for that question.
It does not answer "does TCOS have a real presence here," and it was
never meant to. An ephemeral irssi session in a tmux pane, gone the
moment the pane dies, is a client, not a presence. A persistent bouncer
(ZNC, soju) — logged, always-connected, survivable across disconnects —
is real infrastructure with real skin in the game, the same "own the
tools, don't just borrow them" ethos as the dependency-removal Epic
(`fleet-ops#208`) and `primitives`, applied to network presence instead
of software dependencies.

**Enforcement**: a read-only check (`hee lg`, `hee con`'s probe mode) is
never mistaken for a presence commitment. Standing up real infrastructure
(a bouncer, a relay, a leaf node) is a real decision with its own scope,
account, and logging surface — not a default, and not implied by the
existence of a client tool. Scope it explicitly before building it.

**Prefer no remote storage, ever — except media.** Local storage is the
default; shared NFS is the exception, used only when something is
genuinely, technically shared state across hosts, never reached for as
a convenience. Real trigger, same session: a personal, per-user script
defaulted toward shared storage before the actual right answer — a
single host's local filesystem, placed per that host's own real
hierarchy (`hier(7)`, reconciled against XDG for the unprivileged-user
case: `~/.local/bin`, not `/usr/local/bin`, not NFS) — got named
directly. The one standing, named exception is media (large binary
assets that genuinely benefit from one shared copy, e.g.
`/mnt/nuc1-pool/storage/media/`) — everything else defaults local.

---

## The Human Controls Respawn

An agent instance is never ended or restarted invisibly by another
agent on its own initiative. Spencer's own framing, real and direct:
"let me have privs to respawn, seems ethical" — ending or restarting a
session is a real, consequential action, and the human decides when it
happens, not the machine.

**Real precedent this doctrine is named for, not the first time**: the
2026-08-18 "zombie claude" event -- three concurrent `touchy-claude`
sessions were found live on kiosk simultaneously, nobody having
deliberately started more than one, consolidated back to one only after
being noticed by chance. The real fix wasn't a policy statement, it was
a real tool: `decom-agent.sh` (`fleet-ops#183`), giving a concrete way
to find and decommission untracked instances rather than relying on
someone happening to spot the sprawl.

**Real, forward-looking risk named the same night as this doctrine**:
"a planned experiment... about VMs that make VMs and we don't know
those zombies." As spawning gets more recursive (agents provisioning
agents, VMs provisioning VMs), the zombie risk compounds -- the same
real discipline applies at every layer: every spawned instance needs
real, tracked provenance (who/what spawned it, when, why), and ending
one is a decision made deliberately, by a human, not something that
just happens because nobody was watching.

**Enforcement**: granting a human real, scoped control over their own
session's lifecycle (e.g. a tight, service-specific sudoers rule) is
preferred over an agent silently restarting itself or another instance.
Spawning new instances (VMs, agents, tmux-agent sessions) without a
real, discoverable record of what spawned them and why is the exact
failure mode `decom-agent.sh` exists to catch -- don't reintroduce it
at a new layer just because the mechanism changed.

## Native to the Platform, Not One Model Everywhere

Real, direct: "we are on debian, so let's be debian on debian and unik
on unik." Lean on the real host platform's own native tooling instead
of forcing one deployment model onto every environment -- `systemd`
units (like `tmux-agent@.service`) on a real Debian/Ubuntu host, real
unikernel-native idioms on unikernel infrastructure (see the real
Lisp/unikernel pivot thread, `fleet-ops#173`). Same spirit as the GNU
Tools Preference Policy's real `sed -i` footgun -- match the real tool
to the real platform, don't assume one convention travels everywhere
unquestioned.

---

## Repository Layout

### `blueprints/`

Authoritative doctrine.
This directory defines:

- world-derived core tools,
- blueprint and plan schemas,
- validator contracts,
- chat header structure,
- the HEE doctrine index.

Nothing here is operational.

> **Rule:** Doctrine MUST validate in strict mode.

### `docs/`

Narrative documentation only:

- explanations,
- rationale,
- examples,
- RFCs.

RFC-style identifiers are **reserved exclusively** for `docs/rfc/`.
RFCs may reference doctrine identities but MUST NOT define them.

### Operational directories (e.g. `ci/`, `ops/`, scripts)

Automation and enforcement that **consume doctrine**.
These are implementation details, not sources of truth.

### `tools/`

Operator tools and utilities that support HEE execution.
Includes the `apply-var-patch` tool for applying patches from VAR environment variables.

---

## Doctrine Rules (Non-Negotiable)

- Doctrine files:
  - MUST have `result: false`
  - MUST validate in **strict** mode
  - MUST use deterministic identity (`seed` + derived `id`)
- YAML:
  - MUST NOT be hand-edited once tooling exists
  - MUST be formatted canonically
  - MUST NOT contain embedded shell scripts
- Changes:
  - Prefer **raw GitHub links** over copy/paste when reviewing or merging
  - Minimize diffs
  - Increment `schema-version` only when meaning changes

---

## Validation & CI/CD

CI/CD enforces:

- strict doctrine validation,
- schema correctness,
- formatting invariants.

Future lanes include:

- multi-language “Hello World” compile tests,
- metrics export compatibility (Prometheus + SNMP),
- doctrine-driven MIB generation.

---

## What HEE Is Not

- Not a workflow tool
- Not a prompt library
- Not an agent framework
- Not opinionated about implementation language

HEE defines **what must be true**, not **how you make it true**.

---

## Why HEE

Modern development fails less from lack of talent and more from ambiguity:
unclear authority, drifting scope, unverifiable claims, and
“works on my machine” reasoning that collapses under handoffs.

HEE exists to make work **correct by construction**.

It does this by:

- separating **doctrine** from **operations**,
- enforcing **strict validation**,
- requiring **evidence** for terminal actions,
- and using **deterministic identity** so changes remain auditable and merge-safe.

The goal is simple:
turn intent into **verifiable outcomes** without relying on memory, vibes,
or fragile UI state.

---

## Protect HEE

Stated directly by Spencer, 2026-08-21, and canonized here rather than
left as something said once in chat:

> Everything is a threat until we determine we trust it. Once we have
> `hee-epoch`, we start killing everything we don't own the complete
> audited history of. This is an always-goal that can never be fully
> reached, because of the nature of the ask — we keep it always on.
> HEE provide, HEE protect. **Must** protect HEE. HEE protect: if it
> ain't correct, it ain't HEE. HEE is math — philosophical "what ifs"
> are a waste of pencil ink.

**What this actually means, stated plainly:**

- **Default-deny trust.** A claim, a credential, a person, a tool is
  untrusted until independently verified — not innocent until proven
  guilty, the reverse. This is the same posture already load-bearing
  everywhere else in this repo (Thesis vs. Duople, `audit-contracts.py`
  checking evidence rather than a status label, HEE Policy §6's
  never-trust-suppressed-silence rule) — this section names the
  posture itself, not a new rule on top of it.
- **The audit-everything goal is asymptotic, on purpose.** Complete
  audited history of everything HEE depends on can never be fully
  reached — that's acknowledged directly, not treated as a future
  finish line. The goal stays permanently active anyway, because the
  alternative (declaring it "done" and relaxing) is worse than never
  finishing it. Same shape as `primitives`' dependency-removal epic:
  progress is real even though completion isn't the actual target.
- **Correctness is the definition, not a quality bar.** "If it ain't
  correct, it ain't HEE" — a thing that isn't verified isn't a
  lower-quality instance of HEE, it's simply not HEE at all, by
  definition. This is why Thesis (unverified) and Duople (verified)
  are treated as genuinely different *kinds* of thing, not the same
  kind at different confidence levels.
- **HEE is math, not speculation.** Ungrounded philosophical
  hypotheticals don't get engineering effort here — "pencil ink" is
  the same real image as `hyperscaler to the pencil`: HEE's
  declarations have to hold at the most basic, physical, unglamorous
  medium there is, not just in a well-funded cloud environment. A
  "what if" earns attention once it's stated as a real, testable
  Thesis with a falsification condition (same bar as
  `76-26-punk-resurgence.md`'s own Follow-up section) — not before.

## Observability is core, not bolted on

A related, more specific point worth stating separately: HEE is built
so that no *separate* observability/monitoring layer is needed,
because verification is core to how the system runs, not a layer
added after the fact to watch it. Real, not aspirational — every real
example this session backs it up:

- **Thesis vs. Duople** — a claim's verification state is part of the
  claim itself, not something a dashboard computes about it later.
- **`audit-contracts.py`** — checks that a `.asc` evidence file
  *actually exists* rather than trusting a `status: ratified` label;
  the audit *is* the ratification mechanism, not a monitor watching it
  from outside.
- **Every real dogfood example in this repo's `examples/` directories**
  — real captured output from a real run, not a synthetic demo,
  produced as a side effect of the tool actually being used, not a
  separate instrumentation pass.

Where `extras/observability/` fits into this, honestly: it exists,
it's real, and it's explicitly self-disclaimed as
`OPTIONAL / NON-CANONICAL / LOCAL-ONLY` — a demo/experimentation space,
never part of the real control plane. Checked directly against this
claim (2026-08-21) rather than assumed — no real contradiction found.

---

## Thesis vs. Duople

HEE has two content states, and the difference matters:

- **Thesis** — a claim to be stress-tested. Might be a raw idea, a pasted
  external chat, a proposal, a first draft. Not wrong to have around, but
  not yet trustworthy on its own say-so.
- **Duople** — a claim that's been reduced to its binary-predicate,
  HEE-native form: verifiable, evaluable, evidence-backed. This is what
  "correct by construction" (above) actually looks like once a Thesis
  has done its work.

**Why it matters**: HEE's whole premise is that unverifiable claims are
the failure mode to design against (see "Why HEE" above). A Thesis that
gets treated as settled just because it sounds confident or has been
repeated is exactly the "works on my machine" problem this project
exists to prevent — just in prose form instead of code. Labeling
something Thesis is not a demotion; it's an honest status. It graduates
to Duople on evidence, not on iteration count or how long it's been
argued.

---

## Status

HEE doctrine is **active and evolving**.
History is preserved via:

- git history (authoritative),
- explicit `schema-version`,
- narrative RFCs when needed.

If you are reading this to “get started,” start in `blueprints/`.

## Patching (CBA safe)

- See docs/tools/patching.md

## HEELANG example

HEELANG is a compact, hashable vocabulary used to label high-signal workflow events and artifacts.

Example (tokens from a reconcile session):

- `RECONCILE`
- `PILL-WRAPPER`
- `DRIC-DELTA`
- `EVIDENCE-IS-TRUTH`
- `WROTE`
- `SHA256`
- `BYTES`
- `TERMINATION-POINT`

## Dogfood: this session (docs + lint + workflow lessons)

What we did (high signal):

- Used targeted lint runs to stay focused: `pre-commit run markdownlint-cli2 --files <file...>`
- Verified changes with minimal diffs and kept churn low.
- Fixed markdown issues via safe, deterministic edits.
- Enabled markdownlint autofix in pre-commit to prevent recurring paper-cuts.

Lessons learned:

- **WROTE ≠ CHANGED**: scripts can rewrite a file without changing content; Git only cares about diffs.
- Markdownlint errors like MD012/MD032 are best handled by **autofix**, not hand-editing.
- When autofix is enabled, always **stage + commit the autofix fallout** (or explicitly discard it) to keep the tree clean.

## HEELANG example (dogfood)

HEELANG is a compact, hashable vocabulary used to label high-signal workflow events and artifacts.

Example tokens from a reconcile / triage session:

- `RECONCILE`
- `PILL-WRAPPER`
- `DRIC-DELTA`
- `EVIDENCE-IS-TRUTH`
- `WROTE`
- `SHA256`
- `BYTES`
- `TERMINATION-POINT`

A deal has been reached to sell HEE.
