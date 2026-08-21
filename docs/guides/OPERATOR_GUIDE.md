# TCOS Operator Guide

Canonical, org-wide reference for how a **human** runs the org's
scripts and tools directly. Distinct from
[`GIT_GH_WORKFLOW.md`](GIT_GH_WORKFLOW.md), which governs what *agents*
may do with raw git/gh commands — this doc is about you, at a keyboard,
running things yourself.

Every other repo's own operator doc (where it has one) should be short
and link back here for shared conventions instead of repeating them.

## Prerequisites

- `gh` CLI, authenticated (`gh auth status` to check)
- For scripts requiring YAML parsing (Python-stage tools): `pip install pyyaml`
- Org repos are cloned wherever you keep them — most tools here take a
  `--repo OWNER/REPO` argument rather than assuming a fixed clone path

## The tool-maturity convention: shfn → sh → bash → py → go

Tools here start as tiny incubating shell functions and graduate to
more capable languages as they prove out (documented at length in
`hee/cards/uiboss-repohub-next.wip.yaml`). In practice, as an operator:

- A `*.shfn.bash` file in `library/bash/` is a **function you source**,
  not a standalone script — `source library/bash/rg.scan.shfn.bash`
  then call `rg_scan '<pattern>'`.
- A `bin/*.py` file is a **standalone script** you run directly
  (`python3 bin/tool.py ...` or `./bin/tool.py ...` if executable).
- The eventual destination for a mature tool is a real `hee` subcommand
  (`cmd/hee/`, currently a stub) — not built yet for most tools, this
  is where things are headed, not where they are today.

Don't be surprised that two tools solving similar problems live in
different languages — that's the graduation ladder working as
intended, not inconsistency.

## Worked example: creating a real Epic

This is the concrete, most-asked-about operation, so it's the
flagship example. "Epic" here means a parent GitHub issue with real
linked sub-issues (native GitHub feature — a progress bar GitHub
renders itself) plus a spot on a Project board, not a bare issue with
a hand-written checklist of links (that pattern was found to be
mostly fake in `fleet-ops#188` — only 1 of ~23 "linked" issues was
actually a real sub-issue).

Doing this by hand is 3 separate steps with no single `gh` subcommand
for the middle one (`addSubIssue` is GraphQL-only). Use
[`create-epic.py`](https://github.com/Twin-Cities-Open-Systems/.github/blob/main/bin/create-epic.py)
in the `.github` repo instead:

```bash
# 1. Write the epic body to a file (gh issue create --body-file, not --body,
#    for anything longer than a one-liner)
cat > epic-body.md <<'EOF'
## What
... real content ...
EOF

# 2. One command: creates the issue, links sub-issues, adds to a project
python3 .github/bin/create-epic.py \
  --repo Twin-Cities-Open-Systems/YOUR-REPO \
  --title "Epic: Your Epic Title" \
  --body-file epic-body.md \
  --label documentation \
  --sub-issue Twin-Cities-Open-Systems/some-repo#123 \
  --sub-issue Twin-Cities-Open-Systems/other-repo#45 \
  --project Twin-Cities-Open-Systems/1
```

It reports each step (issue URL, which sub-issues linked or failed,
whether the project add succeeded) — read the output, don't assume
success from a clean exit.

To add sub-issues to an **existing** epic later (the tool only wires
up sub-issues at creation time right now), the raw GraphQL pattern it
wraps is:

```bash
PARENT_ID=$(gh api graphql -f query='query { repository(owner:"ORG", name:"REPO") { issue(number:N){id} } }' --jq '.data.repository.issue.id')
CHILD_ID=$(gh api graphql -f query='query { repository(owner:"ORG", name:"REPO2") { issue(number:M){id} } }' --jq '.data.repository.issue.id')
gh api graphql -f query="mutation { addSubIssue(input: {issueId: \"$PARENT_ID\", subIssueId: \"$CHILD_ID\"}) { subIssue { number } } }"
```

Sub-issues work cross-repo (confirmed live, 2026-08-20).

## Managing a Project board declaratively

GitHub Projects have no native file-based config — everything is the
GraphQL API. [`manage-project.py`](https://github.com/Twin-Cities-Open-Systems/.github/blob/main/bin/manage-project.py)
(also in `.github`) wraps it so a YAML file can be the source of truth
for a project's views and items:

```bash
# Seed a config from whatever's actually live right now
python3 .github/bin/manage-project.py dump Twin-Cities-Open-Systems 1 > roadmap.yaml

# Edit roadmap.yaml, add/remove views or items, then:
python3 .github/bin/manage-project.py apply roadmap.yaml
```

Idempotent — re-running `apply` with nothing changed does nothing
(everything reports "already present, skipping").

## When you hit something that needs a UI

If a task genuinely can't be done without clicking through a browser
(no CLI/API path exists), that's not just a fact to note — file it as
a `glass-ops` issue so it's tracked toward `glass-browser` (Playwright
automation) actually closing the gap, rather than staying a one-off
manual chore forever. See `glass-ops#7` for a real example.
