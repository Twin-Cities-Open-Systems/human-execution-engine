# Documentation Policy

Not all documentation in this org is the same, and treating it as if
it were is exactly how a bulk content-generation pass overwrote
14 repos' real READMEs with unfilled template placeholders on
2026-08-20/21 — the incident this policy exists partly to prevent a
repeat of. This doc has two jobs: name the real types of documentation
that exist here, and state the writing rules that apply across all of
them regardless of type.

**Platform independence.** This repo is the root source of HEE
doctrine/information — not GitHub config. It currently lives on GitHub
and plenty of its live workflow (contracts, issues, cross-repo links)
uses GitHub's own machinery, but that's a hosting choice, not a
property of the doctrine itself. If HEE moved to a different git
server (see [fleet-ops#155](https://github.com/Twin-Cities-Open-Systems/fleet-ops/issues/155),
the tracked on-prem plan), the actual content and rules in this repo
should work the same. Contrast with
[`.github`](https://github.com/Twin-Cities-Open-Systems/.github),
whose whole job *is* GitHub-org administration — GitHub-coupling is
correct and expected there, not here.

`tcos/.github` and `tcos/hee` are the two centers *of this org*.
Anything outside both is an **`ORG`** — see
[`guides/EXTERNAL_SURVEY_METHODOLOGY.md`](guides/EXTERNAL_SURVEY_METHODOLOGY.md#term-org)
for that term and how an `ORG` gets compared against `ORG:tcos/hee`.

## Documentation types

Each type has its own real audience, authority level, and (where one
exists) its own specific guide. This policy doesn't replace those —
it's the index, and the home for rules that cut across all of them.

| Type | Lives in | Authority | Specific guide |
|---|---|---|---|
| **Doctrine / Blueprints** | `blueprints/` | Authoritative, non-terminal (`result: false`), changes must be deliberate and minimal | [`docs/CONTRIBUTING.md`](CONTRIBUTING.md) |
| **Contracts** | `hee/contracts/` (schema here, live signed instances in `fleet-ops`) | Real, cryptographically signed authority — the actual binding relationship, not a description of one | — |
| **Cards / Pills** | `hee/cards/`, `hee/pills/` | Structured working notes — decisions, WIP evidence, seed vocabulary. `Card` for a durable typed record, `Pill` for lighter-weight WIP/evidence. Not authoritative on their own | — |
| **RFCs** | `docs/rfc/` | Narrative proposals. May *reference* doctrine identities, must **not** *define* them | — |
| **Narrative docs** | `docs/` (general) | Explanations, rationale, examples, history — not a source of truth, describes one | — |
| **Operator Guides** | `docs/guides/`, repo-root `OPERATORS.md` | How a **human** runs the org's scripts/tools directly | [`docs/guides/OPERATOR_GUIDE.md`](guides/OPERATOR_GUIDE.md) (central), per-repo `OPERATORS.md` links back to it |
| **READMEs** | repo root | Real, repo-specific entry point — never generic boilerplate (see the incident above) | — |
| **Postmortems** | `docs/postmortems/` | Record of what happened and why, after the fact | — |
| **State Capsules** | per `STATE_CAPSULE_GUIDE.md` | Point-in-time session/state snapshot | [`docs/STATE_CAPSULE_GUIDE.md`](STATE_CAPSULE_GUIDE.md) |
| **Examples / dogfood output** | `examples/` (repo root), in whichever repo the tool lives in | A real run's actual output, not a hand-written mockup | This policy, §6 below |

If you're not sure which type something is, that's a signal to
figure it out before writing it — a Card written as if it were
doctrine, or a README written as if it were an RFC, causes real
confusion about how much weight the content is supposed to carry.

## Rules that apply across every type

### 1. Thesis vs. Duople — label unverified claims honestly

Already real doctrine (see the main [`README.md`](../README.md)'s
"Thesis vs. Duople" section) — restated here because it's a
documentation-writing rule, not just a philosophical point. A **Thesis**
is a claim to be stress-tested — a raw idea, a first draft, unverified.
A **Duople** is reduced to its binary-predicate, evidence-backed form.
Writing a Thesis is not a demotion; presenting one *as* a Duople
(settled fact) when it hasn't earned that status is the actual
mistake.

### 2. Human vs. machine — prefer the real pair, `agent`/`oper`, not generic "agent(s)"

**Sharpened 2026-08-27** (Spencer, direct): this used to only say what
*not* to do; it now names the real replacement. When process or
documentation prose distinguishes what a **human** does from what a
**machine** does, use the canonized pair from `GLOSSARY.md` — `Agent`
(machine-rights party) and `Oper` (human-rights party) — rather than
generic, unqualified "agent(s)" trying to cover both. Same shape of rule
as the org's existing "no vendor names in generic docs" convention, one
level further. (Separate from this: "agent" as a vendor-neutral naming
choice in code/config/identity labels — e.g. preferring it over a
vendor-specific name like "claude" — is a different concern at a
different layer and is unaffected by this rule.)

### 3. Real links, not shorthand

Reference other issues/PRs/docs with real markdown links
(`[fleet-ops#199](https://github.com/.../issues/199)`), not bare
`#199` (ambiguous across repos) or unlinked prose mentions.

### 4. No unfilled template placeholders, ever

If a template has a field like `[Insert the precise Purpose...]`, that
field gets filled in with real content before the file is committed,
or the template isn't used at all. A placeholder committed to a repo
is worse than no file — it reads as real content at a glance. This is
the direct, concrete lesson from the 2026-08-20/21 incident: a bulk
script wrote this exact pattern into 14 repos' README files, and it
sat there, live, on `main`, in several cases including a real
production system's repo, until it was caught.

### 5. Don't write a doc type's authority into the wrong type

A Card is not a Contract. An RFC referencing a doctrine identity is
not the same as an RFC defining one. A narrative doc in `docs/`
explaining a decision is not the decision itself. Keep the type's
real authority level in mind while writing, not just its format.

### 6. New operator-facing tools: dogfood it, document it, save the example

Every time a new tool or process is built for a human to interact
with directly, three things happen **while building it, not after**:

1. **Dogfood it for real** — run it against real data before calling
   it done. Not a synthetic/mocked example; a real invocation against
   something real. (Three real instances already: `create-epic.py`
   creating the actual operator-docs epic, `manage-project.py`
   dumping/applying the real Roadmap project, `survey-github-org.py`
   surveying the real `pallets` org — the last one caught a real bug
   in the process that a synthetic test wouldn't have hit.)
2. **Document it** — a real operator doc entry (this repo's
   `OPERATOR_GUIDE.md` for central conventions, or the tool's own
   repo's `OPERATORS.md`), not just a `--help` string.
3. **Save the dogfood run as a real example**, in `examples/` at the
   root of **the repo the tool actually lives in** (its intended
   audience's repo — a `.github`-hosted tool's example lives in
   `.github`, not here), named `examples/<tool-name>-<case>.<ext>`.
   Referenced from that repo's operator doc, next to the tool's own
   entry. This is a real run's real output, not a hand-written mockup
   of what output might look like — the whole point is that a human
   reading it can trust it reflects what actually happens.
