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

### 7. Every public-facing page is a real, maximized metadata surface

**Added 2026-08-27** (Spencer, direct, several messages in the same
session): "all pages must be OG compliant," "we want to take full
advantage of OG, exif data for any and all img we host, and anything
else we can think of to make our data more dense," "we spread our name
through every possible 'free/passive' means possible," "bake in 'seo'
by default." Not aspirational — a standing requirement for every page
this org publishes, checked the same way a broken link or an unfilled
placeholder would be.

Concretely, every page the org publishes (view.lab, any future public
site) ships with:

1. **Full Open Graph tags** — `og:site_name`, `og:title`,
   `og:description`, `og:type`, `og:url`, plus `twitter:card`. A
   `title` alone is not compliance.
2. **Baked-in SEO** — a real `<meta name="description">` (not a
   truncated copy-paste of the body) and a `<link rel="canonical">`
   pointing at the page's own real, stable URL.
3. **EXIF metadata on every hosted image** — real, filled-in fields
   (at minimum description/credit/copyright), not stripped-and-blank.
   Applies the moment this org hosts its first real image asset, not
   deferred until it feels relevant.
4. **A real favicon** — a placeholder ("not blank") is acceptable only
   as an explicitly-marked stopgap while a real icon set is still an
   open decision; it is never acceptable to ship with no `<link
   rel="icon">` at all.
5. **Real, non-fabricated values only** — every field above is either a
   real fact about the page (a real URL, a real description of what the
   page actually is) or, where no real value exists yet (an unchosen
   favicon, an unpicked license), an honestly-labeled placeholder that
   says so — never an invented value that merely looks complete. Same
   "never fabricate" standard as everywhere else in this org's doctrine,
   applied to metadata specifically because metadata is exactly the
   kind of field a human won't glance-check the way they'd check body
   text.

Real, shipped precedent: `bin/render-review.py` (`.github`) — every
page it generates carries this full block, plus a real `lu:`
(last-updated: ISO timestamp, human-readable, live delta),
commit-or-honestly-uncommitted label, and looked-up (not assumed)
`LICENSE` detection. The org's 6 hand-authored `view.lab` pages
(`index.html`, `roadmap.html`, `review.html`, `follow-up.html`,
`ian.html`, `todo.html`) were retrofitted with (or, for `todo.html`,
built from scratch already carrying) the same block the same day this
rule was written — see [`.github`#42](https://github.com/Twin-Cities-Open-Systems/.github/issues/42)
for the related real gap that surfaced doing that (those pages have no
local git source of record yet, so their `commit:`/`license:` fields
are honest placeholders, not real per-page values — rule 5 applies:
that's a real limitation to disclose, not paper over).

**"Deploy a new page" means reuse, not invent.** Standing definition,
added the same day as the rest of this rule: whenever the real
instruction is to "deploy a new page" (or a gallery, or a blog index —
any new content surface on an existing site), that means take the
current site's real design system as-is — site-bar, theme toggle,
font-size toggle, the metadata block above, the same CSS custom
properties — and reuse it verbatim for the new content. It does **not**
license adding a new UI mechanism (comments, search, pagination, a new
color token) as a side effect of "just" deploying a page. A genuinely
new mechanism is its own explicitly-scoped request, decided on its own,
never smuggled in under a page-deploy instruction. Real precedent:
`todo.html`, built 2026-08-27 by cloning `follow-up.html`'s exact head/
CSS/script scaffold rather than designing new chrome for it.

### 8. Real API tokens/secrets always go through `hee-cred`, never a plaintext file

**Added 2026-08-28**, real trigger: while pursuing a real Cloudflare
API token for a real DNS zone dump, an agent created a plaintext `.env`
file (account ID + a placeholder token field) as a stopgap — the wrong
mechanism. This org already has a real one:
[`hee-cred`](../man/tools/hee-cred.1.md) (`tooling/bin/hee-cred`) —
GPG-encrypted, git-trackable ciphertext (`.hee/secrets/<account>.gpg`),
exec-only retrieval (`-pass <account> -exec <cmd>`, secret handed to
the child process via `$HEE_CRED_PASS`, never printed, never in argv).
Sealing (`-seal <account> -recipients <gpgid,...>`) deliberately
refuses to run without a real interactive TTY — a real, load-bearing
safety property, not a gap to work around with a script or a
non-interactive stopgap.

**Standing rule**: any real API token, password, or similar secret
this org's tooling needs gets sealed via `hee-cred -seal`, retrieved
via `hee-cred -pass ... -exec ...`, and referenced by its real account
name in docs/scripts — never written to a `.env`, a config file, a
chat message, or any other plaintext location, even temporarily or as
a placeholder-to-be-filled-in-later. An agent that needs a credential
it doesn't have asks the real human directly and waits for it to be
sealed properly, rather than improvising a parallel storage mechanism.

**Known real gap, not yet reconciled**: `hee-cred`'s own docs reference
a second, separate tool, `fleet-ops/bin/seal-secret.sh`, for
multi-recipient one-off secret sealing — not yet unified into one tool.
Real, separate open question surfaced 2026-08-28: real sealed
credentials likely already exist for this org (Spencer: "there are a
few to several"), but in a home directory (`/home/touchy`,
`/home/spencer`) this particular sandboxed session's own account
cannot read (`Permission denied`, confirmed directly) — not a "nothing
sealed yet" finding, a real access gap. Don't assume a clean slate
just because one session's search comes back empty.
