% HEE-BOARD(1) | HEE Tools

# NAME

hee-board - real, 0-token curated filtered views over the TCOS Roadmap

# SYNOPSIS

    hee-board [-h] {p0,off-project,open-prs,stale} ...
      hee-board p0                 -- P0 items across every repo
      hee-board unassigned-epics   -- real Epics with no sub-issues linked
      hee-board off-project        -- open issues not yet on the Project board
      hee-board stale --days N     -- items with no update in N days (default 30)
      hee-board open-prs           -- every real open PR org-wide, via `gh search
                                       prs` (not the Project board -- most open
                                       PRs, esp. Dependabot ones, are never added
                                       to it, so board-scoped commands above would
                                       silently miss almost all of them)

    positional arguments:
      {p0,off-project,open-prs,stale}

    options:
      -h, --help            show this help message and exit

# DESCRIPTION

    project, since GitHub Projects v2 has no view-creation mutation in its
    GraphQL schema (confirmed live, 2026-08-24: zero ProjectV2View fields in
    the mutation type) -- UI-only, can't be built once and reused by a
    script. This is the functional equivalent: one real item-list fetch,
    then curated slices printed as plain text. 0-token by design -- pure
    deterministic filtering, no LLM call.
