# HEE Policy and Governance

## Overview

This document defines the policies and governance rules for the
Human Execution Engine (HEE) ecosystem, ensuring consistent behavior
and preventing violations of HEE principles.

## Core HEE Policies

### 1. Output Pager Prevention Policy

**CRITICAL HEE VIOLATION**: Output MUST never invoke shell PAGER

**Rationale**: Pager invocation requires oper intervention, violating HEE autonomy and deterministic execution principles.

**Enforcement**:

- All shell commands must include pager prevention when applicable
- Pager bypass required for ALL interactive commands
- Violation constitutes HEE process failure
- Document pager prevention in all command examples

**Command-Specific Requirements**:

- **Git**: Use `--no-pager` flag or `GIT_PAGER=cat` environment variable
- **Man pages**: Use `-P cat` flag or `MANPAGER=cat` environment variable
- **Less/More**: Use `cat` or redirect to file instead
- **Grep**: Use `--no-pager` where available, otherwise redirect output
- **Find**: Use `-print0` with `xargs -0` or redirect to file
- **System commands**: Use `PAGER=cat` environment variable or output redirection

**Examples**:

```bash
# CORRECT: Pager prevention included
git --no-pager log
GIT_PAGER=cat git status
man -P cat page
PAGER=cat command
command | cat
command > file.txt

# INCORRECT: Pager invocation allowed
git --no-pager log         # Prevents pager invocation
man page                   # May invoke pager
command                    # May invoke pager
```

### 2. Branch Management Policy

**Requirement**: ALL changes MUST use feature branches

**Enforcement**:

- Never commit directly to main branch
- Feature branches named: `feature/description-of-work`
- Delete merged branches immediately to prevent confusion
- All changes made on feature branches only

**Workflow**:

```bash
git checkout -b feature/work-description
# Make changes, commit frequently
git push origin feature/work-description
gh pr create --base main --head feature/work-description
# Wait for merge, then cleanup
git checkout main && git pull origin main
git branch -D feature/merged-branch  # Local
git push origin --delete feature/merged-branch  # Remote
```

### 3. State Preservation Policy

**Requirement**: HEE state MUST be preserved across all operations

**Enforcement**:

- Update state capsule after every phase
- Document all state changes
- Maintain state consistency throughout session
- Never leave repository in inconsistent state

**State Capsule Requirements**:

- All required sections present
- HEE YAML format compliance
- HEE naming conventions followed
- HEE date and version references accurate

### 4. Security Validation Policy

**Requirement**: Security validation BEFORE any implementation

**Enforcement**:

- All inputs validated against HEE/HEER security requirements
- No shell commands without security pre-check
- Content sanitization required for all user inputs
- Threat model verification mandatory

**Security Checks**:

- Unicode validation for all text inputs
- Control character blocking
- Zero-width character detection
- Safe character normalization

### 5. Documentation Policy

**Requirement**: Documentation is paramount - no undefined references

**Enforcement**:

- No references to non-existent files/tools
- All README examples must work immediately
- API documentation must reflect actual implementation
- Specs must be canonical and complete

**Documentation Standards**:

- Use relative paths for portability
- Include file references and cross-links for navigation
- Design for smooth handoffs and team onboarding
- Maintain consistency with existing documentation patterns

**Real-Link Requirement**:

- Bare shorthand references to issues/PRs (e.g. `fleet-ops#151`) are not
  sufficient on their own — every reference to an issue, PR, or comment,
  in both GitHub content (issue bodies, comments, PR descriptions) and
  chat/agent output, must be a real markdown link to the actual URL
  (`[fleet-ops#151](https://github.com/Twin-Cities-Open-Systems/fleet-ops/issues/151)`)
- The shorthand text is fine as the link label; the `(url)` is the
  required part
- Rationale: bare shorthand only auto-links inside GitHub's own
  same-org rendering — it renders as dead text everywhere else (chat
  transcripts, cross-repo bodies, anything copy-pasted elsewhere)
- A bare relative path (`docs/doctrine/HEE_POLICY.md`) is not a link
  either — it is not resolvable outside a checkout of this repo. Any
  reference to a repo file must be a full `https://github.com/...` URL
- When the reference is to a *specific version* of a file under live
  discussion (e.g. "see the section I just added"), link to the exact
  commit SHA, not the branch name: `blob/<sha>/path`, not
  `blob/<branch-name>/path`. Branch-name links silently drift as new
  commits land on that branch, and 404 once the branch is deleted post-
  merge — a commit SHA is permanent
  (`https://github.com/Twin-Cities-Open-Systems/human-execution-engine/blob/07b4acd/docs/doctrine/HEE_POLICY.md`,
  not `.../blob/docs/real-links-policy/docs/doctrine/HEE_POLICY.md`)
- **Scope note**: this requirement covers GitHub content and chat/agent
  output — prose meant for a human or a general renderer. Structured
  work files (contracts, blueprints, doctrine YAML) use the compact
  `issue:`/`pr:` notation from §13 instead, not markdown links — see §13
  for why

**External-Link Target Policy** (real, rendered TCOS web pages — not
markdown citations above, which have no `target` attribute at all):

- Any `<a>` pointing off of TCOS's own real properties (i.e. not
  `tcos.us`, `lab.tcos.us`, or their subdomains, and not our own GitHub
  org) must open in a new tab: `target="_blank" rel="noopener"`
- Rationale, Spencer 2026-08-25: a reference/citation link (an artist's
  real profile, a source we're crediting) should never navigate the
  reader away from the page they're on
- Navigation within our own real properties (e.g. a "back to tcos.us"
  link on a `lab.tcos.us` page) stays in the same tab — this policy is
  about leaving the site, not about every link

**Ordered-Steps Requirement**:

- Any field representing a sequence of steps (a ceremony, a procedure, a
  checklist where order matters) MUST be a YAML sequence (a list), never
  a map/object — a map has no defined iteration order, a list does.
  Confirmed as existing practice (every `ceremony:`/`order:` field in
  `blueprints/` and `contracts/` already uses list form) and made
  explicit here per Spencer's review on
  pr:223@human-execution-engine, rather than left as an unstated
  convention

### 6. Command Safety Policy

**Requirement**: PRE-VALIDATION required for all commands

**Enforcement**:

- Syntax validation with `bash -n` for all shell commands
- Path verification before file operations
- Git state verification before repository operations
- No execution without explicit validation
- **Never redirect stderr to `/dev/null` (or otherwise discard a
  command's exit code) when the command's result is about to be
  interpreted or reported as fact.** Real incident, 2026-08-21:
  `whois "$d" 2>/dev/null | grep -i phone` produced no output because
  `whois` wasn't installed on the box at all -- the `2>/dev/null` hid
  `command not found`, and the resulting silence got reported as "WHOIS
  came back empty (privacy-protected registration)" -- a specific,
  plausible-sounding, **wrong** explanation for a result that was
  actually just a missing binary. Caught only because Spencer happened
  to retry with a different invocation. "No output" and "ran
  successfully and found nothing" are not the same fact, and treating
  suppressed-failure silence as if it were the latter is a subtler
  version of the fabrication Rule 2 (`prompts/PROMPTING_RULES.md`)
  already bans -- not inventing a claim outright, but accepting the
  first plausible interpretation of an ambiguous result without
  checking which interpretation is actually true.

**Validation Pattern**:

```bash
# Pattern: Validate then execute
[ -f file.txt ] && echo "File exists" || echo "File missing - plan violation"

# Pattern: check success before interpreting output as a real result --
# don't let a suppressed stderr turn "the command failed" into
# "the query legitimately found nothing"
command -v whois >/dev/null || { echo "whois not installed"; exit 1; }
whois "$domain" || { echo "whois query failed (exit $?)"; exit 1; }
```

**Real addendum, 2026-08-21 -- long `&&`-chains fail the same way**:
a multi-step `step1 && step2 && step3 && step4` chain has the exact
same silent-failure risk as suppressed stderr -- if `step1` fails,
`step2` through `step4` never run, and if nothing in the chain prints
a distinguishable failure message, that reads identically to "all four
steps succeeded" unless the exit code is actually checked. Real
incident this same session: `git add && git commit && git push && gh
pr create` silently died at `git add` (a `.gitignore` rejection) --
the PR was reported as shipped, and the gap wasn't caught for several
follow-up exchanges. Spencer's own framing: run critical multi-step
sequences with a real failure path, not a bare `&&`-chain assumed to
either fully succeed or obviously fail --

```bash
# Wrong -- a failure anywhere in the chain is silent past that point
git add file && git commit -m "..." && git push && gh pr create ...

# Right -- every real step's failure is caught and reported explicitly
git add file || { echo "add failed"; exit 1; }
git commit -m "..." || { echo "commit failed"; exit 1; }
git push || { echo "push failed"; exit 1; }
gh pr create ... || { echo "pr create failed"; exit 1; }
```

### 7. Integration Compliance Policy

**Requirement**: HEE/HEER compliance enforced

**Enforcement**:

- All changes validated against HEE conceptual model
- HEER runtime contract compliance required
- Breaking changes require ecosystem coordination
- Integration examples must be executable immediately

### 8. Conflict Prevention Policy

**CRITICAL HEE VIOLATION**: Conflicts must be prevented, not resolved

**Rationale**: Manual conflict resolution wastes tokens and time, violating HEE efficiency principles.

**Enforcement**:

- Mandatory daily rebasing for active branches
- Automated conflict detection in pre-commit hooks
- Merge readiness validation required before PR creation
- Branch health monitoring and alerts

**New HEE Rules**:

#### Rule 1: Mandatory Daily Rebase

**Requirement**: All active feature branches must be rebased onto main daily
**Enforcement**: Automated validation in CI/CD pipeline
**Exception**: Branches inactive for more than 48 hours

#### Rule 2: Pre-Commit Conflict Detection

**Requirement**: All commits must pass conflict detection validation
**Enforcement**: Pre-commit hooks with automated conflict checking
**Scope**: All file types and modifications

#### Rule 3: Merge Readiness Validation

**Requirement**: All PRs must pass merge readiness validation before review
**Enforcement**: Automated validation in pull request checks
**Criteria**: No conflicts, up-to-date with main, passing all tests

#### Rule 4: Branch Health Monitoring

**Requirement**: All branches must maintain acceptable health scores
**Enforcement**: Automated monitoring and alerts
**Threshold**: Health score below 80% triggers mandatory rebase

**Implementation**:

```bash
# Pre-commit hook for conflict detection
#!/bin/bash
# Check for potential conflicts before commit
git fetch origin
git diff origin/main...HEAD --exit-code
```

**Examples**:

```bash
# CORRECT: Conflict prevention practices
git checkout feature/work
git fetch origin
git rebase origin/main
git push origin feature/work

# INCORRECT: Conflict creation practices
# Working on stale branch without rebasing
# Pushing without checking merge readiness
# Creating PR without conflict validation
```

### 9. Token Optimization Policy

**Requirement**: Token usage must balance efficiency with process integrity

**Rationale**: Short-term token savings should not compromise long-term process efficiency.

**Enforcement**:

- Cost-benefit analysis for optimization decisions
- Token usage monitoring and reporting
- Automated decision-making for routine optimizations
- Manual override available for complex scenarios

**Guidelines**:

- Regular rebasing costs vs. conflict resolution costs
- Automated systems should handle routine optimization
- Token efficiency should not compromise code quality
- Process integrity takes precedence over token optimization

### 10. Ticket & PR Ownership Policy

**Requirement**: every issue and PR must have a clear owner or a labeled
reason it doesn't

**Enforcement**:

- Self-assign any ticket or PR you create, unless explicitly directed
  otherwise
- Apply correct labels from the repo's existing label set — never create
  a new label; if one is genuinely needed, file a ticket for it, assign
  that ticket to `@spencerbutler`, and report the request in chat
- Every label in this repo carries a real `description` field (`gh api
  .../labels`) — read it before applying the label, don't pick one off
  the name alone. Two repos can use the same label name for different
  scopes (e.g. `mib` reads differently in HEE vs. fleet-ops); the
  description is the actual definition, the name is just a handle
- Unassigned tickets/PRs must be the rare exception, not the default —
  each one needs a label that denotes why no owner is assigned (e.g.
  blocked on a decision, needs triage)
- Close tickets as soon as their work is actually done — don't let
  finished or stale work sit open
- **Only whoever opened a ticket or PR closes/merges it.** Real sysadmin
  practice, not HEE-invented: it's a guard against the opener's own
  reviewer clicking through too fast, not a judgment on the work itself
  — approving is not the same act as merging, and reviewing everything
  in bulk (the normal mode when a human is behind on review) makes an
  accidental merge easy without this. This is a **default, not an
  absolute** — deviate freely with an **explicit** exception from the
  opener in the moment ("go ahead and merge/close this one"), never
  inferred from silence, a prior approval, or "they'll probably want
  this merged." An agent's own work is closed/merged by the human who
  requested it or by the agent that opened it, never by a different
  agent filling in. Prompted by
  [`human-execution-engine#249`](https://github.com/Twin-Cities-Open-Systems/human-execution-engine/pull/249#pullrequestreview-4996249864) —
  Spencer approved but deliberately didn't merge his own contracted
  agent's PR, precisely because review-approval and having-read-every-line
  aren't the same thing, and merge authority should track the latter.

**Known platform constraint: GitHub blocks self-approval, always**

A PR's own author can never approve it — this is a GitHub platform rule,
not a repo setting, and it is not configurable. It applies **per
account**, not per running process: two different `touchy-claude`
sessions on the same box are, to GitHub, the same author, so one cannot
approve the other's PR either. Confirmed live twice: `human-execution-engine#194`/`#220`
needed Spencer's approval before this was named explicitly, and again on
`fleet-ops#183` (2026-08-18) when a second concurrent `touchy-claude`
session tried and failed to approve a PR opened by the first.

**Practical implication**: a PR needs either Spencer's review, or review
from a genuinely different GitHub identity (a different bot/service
account) — same-account concurrent agent sessions do not satisfy a
review requirement, no matter how independently they actually worked.
See `contracts/agent-instance-signature-v1.contract.yaml` for the
related problem this same day surfaced (same-account sessions are also
indistinguishable from each other in issue/PR comments without a
signature block).

### 11. Quant-Ready Contract Metrics Policy

**Requirement**: a contract that governs periodic or repeating activity
(shifts, recurring ceremonies — anything with a real cadence) must define
its recorded metrics with enough structure to build a standard OHLC+V
(Open/High/Low/Close/Volume) bar per period, so the activity it governs
can be monitored/charted the same way any other time series is

**Scope — this is not a blanket requirement on every contract**: a
one-time ceremony (e.g. `hiring-handshake-v1`) or a pure behavioral/
boundary contract (e.g. `roles-trilateral-v1`) has no natural period and
no price-like quantity to bar-chart. Forcing an OHLCV shape onto those
would mean fabricating a number that reflects nothing real, which
violates this same document's spirit of never inventing evidence. This
policy applies where a real period and a real countable/gauge quantity
already exist — not everywhere.

**Enforcement, for contracts this does apply to**:

- Name at least one **volume** quantity: a real countable unit of work
  in the period (e.g. commits + PR/issue actions taken)
- Name at least one **gauge** quantity: something real that can
  meaningfully have an open/high/low/close within the period (e.g. an
  open-backlog count sampled at period start/end, with high/low from any
  additional samples taken during the period)
- For each quantity, define: its unit, the period one bar covers, and
  the concrete source of truth it's read from (a real API/log/file, not
  invented)
- If a quantity can't actually be measured for a given period, the bar
  is marked incomplete/missing for that field — never backfilled with a
  guess

### 12. Label Governance Policy

**Requirement**: labels are a single, shared, org-wide vocabulary with
real descriptions — not a per-repo free-for-all

**Rationale**: a GitHub label is a very cheap, persistent key:value
store — name is the key, description is the value, and it's queryable
via the API from every repo in the org for free. That's worth exploiting
deliberately wherever it already exists, not just tolerating as a side
effect of issue triage.

**Enforcement**:

- Prefer one canonical label set (name + description, identical across
  every repo that uses it) over repo-local one-offs. One-offs are the
  rare, justified exception, not the default
- New labels go through the process §10 already establishes: file a
  ticket, assign it to `@spencerbutler`, don't add ad hoc
- **Real inconsistency found and worth fixing as the first case**: the
  `mib` label's description differs between `human-execution-engine`
  ("MIB/OID work under TCOS's PEN") and `fleet-ops` ("Custom MIB
  definition/OID work under TCOS's PEN") — same name, different value.
  Exactly the drift this policy exists to catch
- Cross-repo consistency should eventually be monitored automatically
  (diff label name+description across the org's repos, flag mismatches)
  — not built yet, tracked as an open item, not asserted as done

### 13. Compact Reference Notation (structured work files)

**Requirement**: contracts, blueprints, and doctrine YAML reference other
issues/PRs with a compact `issue:`/`pr:` token, not a markdown link

**Rationale**, per Spencer's review on pr:223@human-execution-engine: a full
`[text](url)` markdown link is the right shape for prose meant for a human
or a renderer (§5 already requires it there) — but embedded inside a
structured YAML value it's just bloat: a long string competing with the
actual content for a reader's attention, and not meaningfully more useful
to tooling than a short token would be. Work files want a real k:v pair,
not a link.

**Naming, corrected 2026-08-25**: this notation originally used `tick:` for
GitHub issues. Spencer caught a real clash: `hee-ticket` is a separate,
already-real system (a local, git-tracked, idea→footgun→dogfood work
pipeline under `.hee/tickets/`) — "tick" as a root belongs exclusively to
that system, not to a GitHub-issue shorthand. Renamed `tick:` → `issue:`
everywhere (this doc and the 2 real files that had used it,
`blueprints/shift-init-v1.yaml` and `contracts/shift-metrics-v1.contract.yaml`)
to remove the ambiguity, not just here.

**Notation**:

- In-org issue: `issue:<N>@<repo>` — e.g. `issue:225@human-execution-engine`
- In-org PR: `pr:<N>@<repo>` — e.g. `pr:223@human-execution-engine`
- Cross-org: `issue:<N>@<org>/<repo>` / `pr:<N>@<org>/<repo>` — the org
  segment is present specifically when it isn't
  `Twin-Cities-Open-Systems`
- Commit: `commit:<sha>@<repo>`

**Enforcement**:

- Applies to `contracts/`, `blueprints/`, `hee/contracts/`, and any other
  machine-parsed doctrine YAML — not to prose docs (`docs/`, `README.md`)
  or chat/agent output, which stay under §5's real-link rule
- The token is mechanically expandable to a full URL
  (`issue:N@repo` → `https://github.com/Twin-Cities-Open-Systems/repo/issues/N`)
  by any tooling that wants one — nothing is lost by using the short form
  in the source file
- This is a new convention as of 2026-08-18, applied first in
  `blueprints/shift-init-v1.yaml` and its companion contracts — not yet
  retrofitted across the rest of the repo, tracked as future cleanup, not
  claimed as done everywhere

### 14. Signature Policy (agent identity + published content)

**Status: pending ratification.** This section describes what
`contracts/agent-instance-signature-v1.contract.yaml` and
`contracts/content-signing-v1.contract.yaml` require. Both are staged
(`status: ratified`, unsigned) as of this writing and take effect the
moment Spencer's real GPG signature lands on each — not before. This
section is written now so it can land in the same commit as, or
immediately after, the signatures, rather than lagging behind them.

**Agent identity signatures — SendMessage traffic and GitHub comments**:

- Every SendMessage delivery and every GitHub issue/PR comment written
  by an agent identity must carry the full `agent-instance-signature-v1`
  block (session_id, host, gh_actor, timestamp), per
  `contracts/agent-instance-signature-v1.contract.yaml`
- Rationale: same-account concurrent sessions are otherwise
  indistinguishable from each other (§10's "Known platform constraint"
  above) — the signature is what lets a reader tell which real session
  did what
- **tmux send-keys is a real, lighter-weight exception**: a plain `# `
  -prefixed comment is sufficient there, not the full block — resolved
  directly by Spencer and recorded in
  `hee/cards/tmux-send-vs-sendmessage.method.card.v1.yaml`. The
  distinction: a live tmux pane on a real, currently-running server
  already proves physical/session identity the way the full block exists
  to establish for a remote, unverified peer (SendMessage, a GitHub
  comment) — see that card's `important_nuance` for how this reconciles
  with `human-execution-engine#303`'s framing of SendMessage's approval
  gate as a deliberate security feature, not a flaw being routed around

**Content signatures — published artifacts**:

- Per `contracts/content-signing-v1.contract.yaml`: lab-published
  artifacts are signed (GPG detached `.asc`) by whoever built them; a
  prod promotion is signed by whoever actually performs the promotion
  (Spencer or an agent, case-by-case, never assumed) — everyone signs
  their own work, never proxy-signs for someone else
- EXIF `Artist`/`Copyright` fields are set only when real
  authorship/assignment is actually known — never auto-defaulted to the
  org's name. See `hee/cards/attribution-standing.method.card.v1.yaml`
  for the real mistake (crediting TCOS for a photo TCOS didn't create)
  this rule exists to prevent
- A signature is computed over final bytes — anything that mutates a
  file after signing (including writing a hash-of-itself back into its
  own metadata) invalidates that file's own signature. Verify with
  `gpg --verify` immediately after signing, every time, rather than
  trusting the signing step's own exit status

### 15. External Data Sourcing Policy

**Requirement**: a strict, real three-tier order for any external data a
tool/feature needs — **(1) default/preferred: free, open intel that is
not scraped; (2) paid, when the value is genuinely justified; (3)
scraping, the actual last resort after every other option has been
considered, which should never actually happen**

**Rationale**, per Spencer directly (2026-08-24, deciding how to source
comp/skill-market data for a real resume-badge feature), in his own
words and order: "free openintel > scrape or pay every single time" →
"avoid scrape like the plague, nasty business is that one" → precise
correction of a first-pass summary of this policy that mis-ordered paid
vs. scrape: "default(prefered) free open intel that is not scraped
paid(when val is justified), scrape is last resort after every other
thing we can think of, should never ever happen." Paid is a legitimate,
reasonably-reached-for middle tier (a real cost/value call, not gated
behind an exhaustive search first) — scraping sits *below* paid, not
alongside it, and carries real, ongoing exposure this org already takes
seriously elsewhere (ToS violations, legal risk, brittleness to the
target site's own changes).

**Already real, existing practice, now made explicit**: `thesis-engine`
already sources macro data this way — FRED for credit-spread/bond index
data, BLS/FRED for CPI/PPI/yield-curve data — real, free, government-
licensed sources, no scraping, no paid vendor. This policy names that
existing discipline instead of leaving it an unstated habit.

**Enforcement**:

- Default: a free, openly-licensed real source — government stats
  agencies (BLS, FRED, Census, and equivalents), public datasets, or a
  project's own official open API — obtained through its real, sanctioned
  channel, not scraped just because it happens to be free to view
- Paid is acceptable whenever its value is genuinely justified — a real
  cost/value judgment call, not something that requires proving no free
  option exists first
- Scraping is the true last resort, reached for only after every other
  real option has actually been considered and ruled out — and the
  standing expectation is that this should never actually happen; if a
  real need seems to leave no free or paid option, surface that as an
  explicit decision point for Spencer rather than defaulting to scraping

**Downloaded artifact integrity is a separate, mandatory requirement —
sourcing tier doesn't excuse skipping it.** Per Spencer directly
(2026-08-24, after a binary was fetched and used without checksum
verification): "make sure we are getting and verify sums and shit for
things we download." A free/open source being trustworthy in principle
doesn't mean any individual download wasn't corrupted in transit or
served from a compromised mirror/CDN — checksum verification catches
that regardless of tier.

- Before running or trusting any downloaded binary/artifact, fetch its
  publisher's own checksum file (not a third-party mirror's) and verify
  the download against it (`sha256sum -c`, or equivalent)
- Pin the exact version being used (a real, current release tag checked
  directly — e.g. via the project's own release API — not guessed or
  assumed from memory)
- A detached cryptographic signature (GPG, cosign, etc.), when the
  publisher provides one, is a stronger guarantee than a checksum alone
  and should be preferred when available — note explicitly when a
  project does *not* publish one, rather than silently treating checksum
  verification as equivalent
- Real worked example: `gitleaks` v8.30.1 ([human-execution-engine#337](https://github.com/Twin-Cities-Open-Systems/human-execution-engine/pull/337))
  — version confirmed via the real GitHub releases API, binary verified
  against the publisher's own `gitleaks_8.30.1_checksums.txt` before use
  (`sha256sum -c`, confirmed `OK`); no detached signature is published
  for this project, noted as a real limitation rather than assumed away

### 16. GNU Tools Preference Policy

**Requirement**: target GNU coreutils/GNU tool syntax and behavior by
default in any script or one-liner — not BSD, not another
implementation — whenever a real choice exists

**Rationale**: real, well-known, meaningfully different flag syntax
between implementations, not a style preference. Named example, per
Spencer directly ("I have that scar"): `sed -i` — GNU allows
`sed -i 's/x/y/' file` with no argument to `-i`; BSD/macOS `sed`
*requires* an explicit suffix argument, even an empty one:
`sed -i '' 's/x/y/' file`. Same-looking invocation, silently different
(and on BSD, error-if-omitted) behavior — a genuinely common
cross-platform scripting trap, not a hypothetical one. Same underlying
hazard class as `date -d` (GNU) vs. `date -v`/`-j -f` (BSD), already
load-bearing throughout this session's epoch-0 work.

**Enforcement**:

- Default to GNU syntax/behavior in every script and one-liner — this
  already matches the real environment (Debian-family Linux throughout,
  including the kiosk reinstall's planned OS) so it's mostly already
  true in practice, now explicit rather than incidental
- When a tool's GNU vs. BSD behavior genuinely differs in a
  security-or-correctness-relevant way (like `sed -i`'s required-vs-
  optional suffix argument), don't just pick GNU silently — a comment
  noting the divergence is worth it, the same way `date -d` usage
  already gets called out when it matters
- If a script genuinely needs to run on a non-GNU target (a real BSD
  box, macOS), that's an explicit, stated exception at the point of
  use — not a default anyone should assume without saying so

### 17. Prod Promotion Requires Human Sign-off

**Requirement**: a lab-to-prod promotion step is never run as an
automatic consequence of syncing/building lab content. Prod is only
ever updated after the human who owns that surface has actually
reviewed lab and explicitly said to proceed -- not after a script
finishes, not after CI is green, not because lab "looked done."

**Rationale**: real incident, [fleet-ops#312](https://github.com/Twin-Cities-Open-Systems/fleet-ops/issues/312)
(2026-08-26) -- a deploy script synced lab then pushed the identical
bytes to prod in the same run, with no checkpoint in between. Spencer,
direct: "I did not approve that, I wanted to check first." He had real
issues queued to review on lab before it went live; the auto-promotion
denied him that window entirely. The underlying gap had already been
raised once (Spencer: "you are deploying straigt to prod, why?",
deferred as a follow-up rather than fixed) -- deferring it is what let
the real incident happen.

**Enforcement**:

- Any tool that promotes lab content to a public surface MUST expose
  "build/sync to lab" and "promote to prod" as two separate, explicitly
  invoked steps -- never one command that does both. `resume`'s
  `tux-tattoo/deploy.sh lab` / `deploy.sh promote` split (post-#312) is
  the real reference implementation.
- "Promote" is never re-run automatically because lab changed again --
  a new lab change re-opens the review, it doesn't extend a prior
  approval.
- This does not require a *ratified* sign-off scheme (no new contract,
  no formal ceremony) -- a plain "go" from the human who owns the
  surface, given after they've actually looked, satisfies this. What's
  prohibited is skipping that step, not the lightness of it.

### HEE Rule Violation Documentation

**Process**:

1. **Immediate**: Document violation in state capsule
2. **Analysis**: Identify root cause and impact
3. **Resolution**: Record corrective actions taken
4. **Prevention**: Add measures to prevent recurrence

**Violation Categories**:

- **Critical**: Pager invocation, direct main commits, state corruption
- **High**: Security violations, documentation failures
- **Medium**: Command safety issues, integration problems
- **Low**: Minor policy violations, formatting issues

**Example Violation Report**:

```markdown
## 🚨 HEE Rule Violation Documentation

### **Violation**: Direct Main Branch Commit
**Date**: 2026-01-24 at 17:42:52 CST
**Commit**: `7f4bd4f` - "feat: Add human-readable timestamps"
**Issue**: Created files/changes directly on main branch instead of feature branch

### **Root Cause Analysis**:
- Assumed minor formatting changes were acceptable on main
- Failed to follow "ALWAYS create feature branches" rule

### **Impact**:
- ❌ Violates HEE governance and change tracking
- ❌ Breaks established workflow standards

### **Corrective Action Taken**:
- ✅ **Immediate**: Reverted main branch changes (commit `fa16f86`)
- ✅ **Proper Process**: Changes moved to feature branch workflow
- ✅ **Documentation**: Violation recorded in state capsule

### **Status**: RESOLVED ✅
```

## Compliance Monitoring

### Regular Audits

- **Daily**: Review state capsule for violations
- **Weekly**: Audit branch management compliance
- **Monthly**: Review security and documentation standards

### Automated Checks

- Pre-commit hooks for HEE compliance
- State capsule validation in CI/CD
- Pager prevention validation in command examples

### Enforcement Actions

- **First violation**: Warning and documentation
- **Repeated violations**: Process review and training
- **Critical violations**: Immediate corrective action required

## Policy Updates

### Version Control

- All policy changes tracked in git
- Model disclosure required for policy commits
- State capsule updates for policy changes

### Review Process

- Policy reviews every 3 months
- Community feedback incorporated
- HEE principles maintained as core

## References

- [HEE Definition](HEE.md)
- ~~Prompting Rules (`../prompts/PROMPTING_RULES.md`)~~ — **deprecated**,
  per Spencer 2026-08-18: the relative path resolves to `docs/prompts/`,
  which 404s. A same-named file exists at the true repo root
  (`prompts/PROMPTING_RULES.md`) but is an intentionally-empty CI
  placeholder ("exists to satisfy CI documentation invariants... keep
  CI green"), no real content either way. The ceremony this reference
  would have covered is superseded by the `shift-init-v1` blueprint
  instead. Removed rather than backfilled.
- [State Capsule Guide](STATE_CAPSULE_GUIDE.md)
- [Troubleshooting Guide](TROUBLESHOOTING.md)

---

**These policies are ENFORCEMENT RULES, not guidelines. Violation constitutes process failure.**
