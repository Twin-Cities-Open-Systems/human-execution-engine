% HEE-CONTRACT-REVIEW(1) | HEE Tools

# NAME

hee-contract-review - smart-sorted contract review, needed-first

# SYNOPSIS

    hee-contract-review
    hee-contract-review --dump [json]
    hee-contract-review --gopher-menu
    hee-contract-review --action sign --key GPG-KEY-ID --signer 'NAME'
    hee-contract-review [--MODE] help


# DESCRIPTION


    Collects every contract it can find, ranks them most-needed-first, and
    presents that ranking in one of four ways. With no arguments it opens
    the interactive curses TUI.

    What it scans: *.yaml under any contracts/ or hee/contracts/ directory
    one level inside ~/git -- a HARDCODED workspace root, not
    $HOME/git and not the current repo. GitHub URLs are built assuming the
    Twin-Cities-Open-Systems org.

    Worktrees are meant to be excluded -- they are ephemeral working
    copies, never the canonical source for a signature -- but the filter
    only recognizes the `<repo>.worktrees/` path convention. A worktree
    placed anywhere else (for example `<repo>/.claude/worktrees/`) is
    still scanned, and the (repo, relative-path) dedupe does not collapse
    it either, because its relative path differs. Verified live, 2026-08-31:
    a run from inside such a worktree lists every contract twice. Real
    limitation, stated rather than papered over.

    Priority and effort are an HONEST GUESS, labelled as one, not data read
    from the files -- almost no real contract carries a priority or effort
    field. The guess is:

      priority, 0-10, higher = more needed
        8   no status field at all
        7   status not_implemented
        6   status proposed
        5   an unrecognized status
        4   status in_progress or partially_implemented
        1   status ratified or completed
        9   the file failed to parse
        +1  updated-at is more than 5 days old
        +2  "financial", "sovereignty" or "security" appears in the name
        (capped at 10)

      effort, 1-3, lower = quicker
        1   the default -- read and sign
        2   the spec body is longer than 800 characters when stringified

    Every contract carries the reasons behind its own number, so the guess
    can be argued with rather than trusted.

    Sorting is priority descending, then effort ascending. pyyaml is used
    when importable; without it a regex fallback recovers just name, status
    and updated-at, so ranking still works but is coarser.


# ENVIRONMENT

    No environment variables are read. The scan root, the gopher host/port
    and the GitHub org are all hardcoded, so none of them can be pointed
    elsewhere without editing the tool. The default TUI needs a real
    terminal; use --dump anywhere else.


# EXIT STATUS

    Nagios plugin convention.
    0 OK        the mode ran
    1 WARNING   unknown --action, or --key/--signer missing in sign mode.
                Note: usage errors the org vocabulary would put at
                2 CRITICAL; the tool really exits 1 today and is documented
                as-is, not changed here.


# SEE ALSO

    tools/hee/ratify-contract.sh -- the same staging logic, one contract
    at a time

# MODES

    (default)        interactive curses TUI: j/k or arrow keys move, Enter
                     opens a detail view, q or Esc quits. Read-only.
    --dump [json]    plain text or real JSON, no TUI
    --gopher-menu    RFC1436 gopher menu text on stdout
    --action sign    mass-ratify: prompts per proposed contract, then runs
                     gpg on THIS terminal. The only mode that writes.

    Add `help` after any mode for its own page:
        hee-contract-review --action sign help
