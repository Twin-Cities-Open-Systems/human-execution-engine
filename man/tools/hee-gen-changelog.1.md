% HEE-GEN-CHANGELOG(1) | HEE Tools

# NAME

hee-gen-changelog - render CHANGELOG.md from the repo's own merge history

# SYNOPSIS

    hee-gen-changelog [PATH]                 dry run: print what [Unreleased] would become
    hee-gen-changelog [PATH] --write         write it into CHANGELOG.md (created if absent)
    hee-gen-changelog [PATH] --release VER   turn [Unreleased] into "## [VER] - today", then --write
    hee-gen-changelog [PATH] --since REF|DATE   history window (default: the newest dated header)
    hee-gen-changelog help


# DESCRIPTION


    The [Unreleased] block, from conventional-commit subjects; nothing typed.

      Every merge to main is a Conventional Commit with its PR number
      (rule 8: `type(scope): description (#N)`). That is already a changelog;
      this renders it in Keep a Changelog form so nobody types it twice or
      forgets it. Operator, 2026-09-05: "keep a nice change log with the
      updates."

      Grouping: feat -> Added; fix -> Fixed; docs -> Documentation;
      perf -> Performance; a `!` or BREAKING CHANGE -> Breaking; chore,
      refactor, ci, build, test, style, lint, ops -> Changed; anything else
      -> Other. Each line: date, bold scope, the description verbatim, and a
      real link to the PR. The window starts at the newest `## [x] - DATE`
      header in CHANGELOG.md (or --since); merges are skipped.

      DRY RUN IS THE DEFAULT -- the same rule as hee-gen-manpages, for the
      same reason (issue 464). --write replaces only the [Unreleased] block;
      released sections are never touched. --release VER renames the block
      to a dated version header and starts a new empty [Unreleased].

      Because a PR cannot know its own squash subject in advance, the file
      is regenerated AFTER merges, as a chore PR -- the same cadence as the
      gopher man tree. `hee-gen-changelog` with no flags is the check: empty
      output means the file is current.


# EXIT STATUS

    0 OK (dry run rendered, or written)   2 CRITICAL (not a git repo, no window)   3 UNKNOWN
