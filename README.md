# Human Execution Engine (HEE)

[![CI/CD Pipeline](https://github.com/Twin-Cities-Open-Systems/human-execution-engine/actions/workflows/ci.yaml/badge.svg)](https://github.com/Twin-Cities-Open-Systems/human-execution-engine/actions/workflows/ci.yaml)

HEE is a **doctrine-first execution framework** for coordinating human
reasoning, machine assistance, and automation **without ambiguity**. It
prioritizes correctness over consensus, structure over vibes, determinism
over convenience. This repository is the canonical source of HEE doctrine.

---

## The problem

**Records drift from reality. Silently, and mostly discovered by accident.**

Four found in a single day, 2026-09-06, none of them by looking for them:

- A roster listed 3 of 7 people as active. Two of those GitHub accounts had not existed for weeks.
- A host document described a mail server as *"a stub -- no MTA installed, nothing listening."* OpenSMTPD 7.8.0 was installed, running, and listening on four addresses.
- A registry declared `inuid_derivation: sha256(inuid_seed)`. The recorded value did not reproduce from that seed.
- A GPG-sealed credential was committed to a **public** repository inside a pull request titled as a documentation typo fix.

Nobody lied. Every one of those was true when written, or was never checked
in the first place. That is the whole problem:

> **A claim with nothing comparing it to reality decays into a lie, without
> anyone doing anything wrong.**

Agents make this urgent rather than causing it. An agent reads records at
machine speed and acts on them with confidence. This project's own agent
read "mx1 is a stub" and repeated it into an architecture diagram and a
disaster-recovery ticket before a human caught it. The document was already
wrong; the agent propagated it faster than a human would have.

HEE is the machinery for finding that **on purpose instead of by luck**:
typed objects that state what they assert, checks that compare the
assertion against a measurement, and a signature chain recording who
attested to what.

This is not a new idea. Hazard & Haapio described the same mechanisms --
hash-bound references, static records as anchors for intelligence, git as
the transmission medium -- in 2017, without knowing this project would
exist. See [docs/REFERENCES.md](docs/REFERENCES.md).

See [Why HEE](#why-hee) for the mechanisms, and
[Thesis vs. Duople](#thesis-vs-duople) for how a claim earns the right to be
believed.


This repository is the **canonical source of HEE doctrine**.

---

## What it is, in one screen

- **Typed objects.** Every governance record -- Card, Pill, Contract,
  Blueprint, Plan, Registry -- is YAML with a `kind`, a `metadata` block and
  a hash-derived identity (`inuid = sha256(seed)`), validated by `hee lint`.
- **Checks that compare claims to measurement.** `hee check` reconciles the
  roster against real GitHub accounts, verifies every detached signature
  against the file beside it, confirms every identity hash reproduces from
  its seed, and refuses secret paths in a public repo.
- **A signature chain, not a status label.** A contract is ratified by a
  GPG signature over the YAML. The `.asc` beside the file is the evidence;
  the `status:` line is only a claim about it.
- **Doctrine separated from operations.** `blueprints/` and `hee/` define
  what must be true. `ci/`, `tooling/` and scripts enforce it and are never
  a source of truth.
- **Two content states.** A *Thesis* is a claim to stress-test. A *Duople*
  is one reduced to a verifiable, evidence-backed form. Labeling something
  Thesis is honest status, not demotion. (Defined in
  [the org glossary](https://github.com/Twin-Cities-Open-Systems/.github/blob/main/profile/GLOSSARY.md).)

HEE defines **what must be true**, not **how you make it true**. It is not
a workflow tool, a prompt library, or an agent framework, and it has no
opinion on implementation language.

---

## Get started

Without installing anything, in a directory you will delete:

```sh
$ d=$(mktemp -d)
$ git clone -q https://github.com/Twin-Cities-Open-Systems/human-execution-engine "$d/hee"
$ cd "$d/hee"
$ export PATH="$PWD/tooling/bin:$PATH" MANPATH="$PWD/man/tools:"
$ hee check all
$ hee lint
$ hee list
$ cd /; rm -rf "$d"
```

Proven in a clean environment: after the last line, `$HOME` is untouched.
The [quick start](docs/guides/QUICKSTART.md) has the real output of each
tool, the session-only and make-it-stick tiers with their undo, and what
each result is telling you.

Rules for changing this repo: [CONTRIBUTING.md](CONTRIBUTING.md). The rules
an agent reads at session start: [`prompts/PROMPTING_RULES.md`](prompts/PROMPTING_RULES.md).

---

## Where things are

| path | what | authority |
|---|---|---|
| `blueprints/` | doctrine: schemas, validator contracts, the doctrine index | **yes** -- must validate in strict mode, `result: false`, deterministic identity |
| `hee/` | cards, pills, contracts, registries, skills | yes |
| `mib/` | the HEE-MIB vocabulary module under PEN 66582 | yes |
| `docs/doctrine/` | HEE_POLICY and the canon moved out of this file | yes |
| `docs/guides/` | how-tos: QUICKSTART, HEE_EXPLAINED, CONTINUITY, BRANDING_IDENTITIES | no |
| `docs/rfc/` | open questions; RFC identifiers are reserved here | no |
| `docs/REFERENCES.md` | prior art this design converges with | no |
| `tooling/bin/` | the `hee` tools; `library/` holds the shared code | consumes doctrine |
| `ci/`, `tools/` | enforcement and operator utilities | consumes doctrine |

Full taxonomy and writing rules: [`docs/DOCUMENTATION_POLICY.md`](docs/DOCUMENTATION_POLICY.md).
Patching workflow: [`docs/tools/patching.md`](docs/tools/patching.md).

---

## Doctrine that used to live here

Five statements, each grounded in a real dated event and mostly in the
operator's own words, moved intact to
[`docs/doctrine/README_CANON.md`](docs/doctrine/README_CANON.md) so this
file can be a front door: **Skin in the Game**, **The Human Controls
Respawn**, **Native to the Platform**, **Protect HEE**, and **Observability
is core, not bolted on**.

What happens when the primary agent runs out of budget, with each fallback
tier honestly marked proven / designed / not built:
[`docs/guides/CONTINUITY.md`](docs/guides/CONTINUITY.md).

---

## Status

HEE doctrine is **active and evolving**. History is git (authoritative),
explicit `schema-version`, and narrative RFCs when needed.
