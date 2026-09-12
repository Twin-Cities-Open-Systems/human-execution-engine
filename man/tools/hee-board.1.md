% HEE-BOARD(1) | HEE Tools

# NAME

hee-board - real, 0-token curated filtered views over the TCOS Roadmap

# SYNOPSIS

    hee-board [-h] {p0,off-project,open-prs,stale,outsiders} ...
      hee-board p0                 -- P0 items across every repo
      hee-board unassigned-epics   -- real Epics with no sub-issues linked
      hee-board off-project        -- open issues not yet on the Project board
      hee-board stale --days N     -- items with no update in N days (default 30)
      hee-board open-prs           -- every real open PR org-wide, via `gh search
                                       prs` (not the Project board -- most open
                                       PRs, esp. Dependabot ones, are never added
                                       to it, so board-scoped commands above would
                                       silently miss almost all of them)
      hee-board outsiders --roster FILE [--days N] [--allow-bot LOGIN]... [--markdown FILE]
                                   -- PRs and issues filed by accounts outside the
                                       roster: every open one, plus any created in
                                       the last N days (default 7), in every
                                       non-archived org repo

    outsiders:
      "Us" is every GitHub login in the roster file (roster.json: tiers[].people[].github).
      A roster login whose status is departed or inactive still counts as a finding:
      the roster says that account holds no access. Bots are listed separately;
      dependabot[bot] and github-actions[bot] are expected, --allow-bot adds more.

      Severity, per item:
        CRITICAL  an account outside the roster filed on a PRIVATE repo -- it can
                  read that repo, so access is wider than the roster says
        WARNING   an account outside the roster, an unexpected bot, or a roster
                  account marked departed or inactive, filed on a public repo
        UNKNOWN   a repo whose issues could not be read (token scope, rate limit)
        OK        nothing filed from outside the roster
      Exit code is the worst of these, in that order: 2, 1, 3, 0.

    positional arguments:
      {p0,off-project,open-prs,stale,outsiders}

    options:
      -h, --help            show this help message and exit

# DESCRIPTION

    project, since GitHub Projects v2 has no view-creation mutation in its
    GraphQL schema (confirmed live, 2026-08-24: zero ProjectV2View fields in
    the mutation type) -- UI-only, can't be built once and reused by a
    script. This is the functional equivalent: one real item-list fetch,
    then curated slices printed as plain text. 0-token by design -- pure
    deterministic filtering, no LLM call.
