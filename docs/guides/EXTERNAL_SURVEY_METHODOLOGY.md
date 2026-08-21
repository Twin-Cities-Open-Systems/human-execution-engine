# External Survey Methodology

How to size up an unfamiliar organization or information store from
the outside — what to look at, in what order, to answer "what is this,
how mature is it, how does it actually govern itself" without having
to read everything by hand. First concrete implementation is a GitHub
org/repo surveyor (`.github/bin/survey-github-org.py`) — the methodology
itself isn't GitHub-specific and should extend to other information
stores (a different git host, a wiki, a docs site) later.

## The five dimensions

Any external store gets sized up along the same five axes, regardless
of what platform it's on:

### 1. Identity & scale
What is this, concretely — not the marketing description, the actual
footprint. How many repos/units exist, how old is it, what
languages/technologies actually show up.

### 2. Governance & documentation
Does it have a stated policy for how it's maintained — a contribution
guide, a code of conduct, a security policy, a license (and is it
consistent across the org or does it vary per-repo)? Does it have an
org-level default/config surface (GitHub's `.github` repo is one
concrete instance of this pattern) or is governance ad hoc per-repo?

### 3. Access & visibility
What's actually visible from the outside vs. what exists but is
gated. Don't assume total repo count from what an unauthenticated
survey can see — say explicitly what's public vs. inferred vs.
unknown.

### 4. Tooling & process signals
CI presence, issue/PR templates, CODEOWNERS-equivalent, dependency
scanning — the operational maturity signals, not the stated
intentions. A repo can claim a process in its README and not actually
run it (see [[documentation-policy]]'s placeholder-content lesson —
the same "looks real, isn't" failure mode applies to surveying someone
else's repo, not just writing your own docs).

### 5. Activity signals
Is this alive or dormant — recency of commits/releases across the
top repos, not just the flagship one. A single actively-maintained
repo inside an otherwise dormant org is a different picture than
uniform activity.

## Output: a filled template, not a data dump

The point of a survey is a report a human can actually read in one
pass, not a directory of raw API responses. Each dimension above gets
a short section: what was found, and — critically — what's
**unknown/unverifiable** from outside rather than silently omitted.
An honest "couldn't determine X from public access" is more useful
than a guess presented as fact.

## Applying this beyond GitHub

The five dimensions are meant to transfer directly: swap "repos" for
whatever the store's actual unit is (packages, pages, documents),
"CI/CODEOWNERS" for whatever process-maturity signals that platform
has, "commits" for whatever activity trail exists. The GitHub
implementation is the first real instance, not the ceiling.
