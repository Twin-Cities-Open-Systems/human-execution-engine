% HEE-TICKET(1) | HEE Tools

# NAME

hee-ticket - repo-local tickets, stored as real YAML in git

# SYNOPSIS

    hee-ticket -new "DESCRIPTION" [--source WHERE] [--ref URL] [--tag T[,T...]]
    hee-ticket -list [SPEC] [--open | --closed]
    hee-ticket -advance ID [--why TEXT]
    hee-ticket -back ID --why TEXT
    hee-ticket -close SPEC [--why TEXT]
    hee-ticket -html [--workspace [DIR]] [--out FILE]
    hee-ticket -json [--workspace [DIR]]
    hee-ticket [-ACTION] help


# DESCRIPTION


    The smallest real, dogfoodable step toward tracking that TCOS owns
    outright, rather than renting from GitHub Issues. It does not replace
    GitHub Issues and does not sync with them -- nothing here reaches the
    network at all.

    Storage is one file per ticket at .hee/tickets/<id>.yaml under a repo
    root. Which repo: --repo NAME (a repo under ~/git), else the repo the
    current directory is inside. From any other directory -- like every hee
    tool, this one runs from anywhere (operator, 2026-09-10) -- the reading
    actions (-list, -html) show every repo under ~/git, one per origin, and
    the writing ones (-new, -advance, -close) ask for --repo rather than
    guess. The files are ordinary tracked YAML: commit them like anything
    else, and read or edit them by hand when this tool cannot express what
    you need.

    Every ticket carries the real idea->footgun<->dogfood cycle as a
    structural `stage` field plus a `stage_history` of timestamped
    transitions -- so stage counts and durations are derived from record,
    never asserted.


# ENVIRONMENT

    No environment variables are read. `git` must be on PATH, the current
    directory must be inside a git repo, and pyyaml must be importable.


# FILES

    .hee/tickets/<id>.yaml   one record per ticket, under the repo root.
                             Fields written by this tool: id, created_at,
                             description, status, stage, stage_history, and
                             when given source, ref, tags, closed_at,
                             closed_reason. Anything else you add by hand is
                             kept and, for -html, shown when it is a string.


# EXIT STATUS

    Nagios plugin convention.
    0 OK        the action completed
    1 WARNING   no action given (this page is printed), not inside a git
                repo, pyyaml missing, or the action's own failure -- see
                each action's page. Note: several of these are UNKNOWN- or
                CRITICAL-shaped in the org vocabulary; the tool really
                exits 1 today and is documented as-is, not changed here.


# EXAMPLES

    $ hee ticket -list                                       # ci
    $ hee ticket -list --open                                # ci
    $ hee ticket -list demo/0002 --workspace tests/fixtures/tickets-workspace   # ci
    $ hee ticket -json --workspace tests/fixtures/tickets-workspace   # ci
    $ hee ticket -html --workspace --out /tmp/tickets.html   # every repo under ~/git; not run in CI


# SEE ALSO

    hee-git-merge -- shares the same id/range/regex selector
    (library/py/hee_range)

# ACTIONS

    -new       open a ticket at stage idea. --source records where it came
               from (a page, a brain dump timestamp, a review); --ref a
               GitHub issue or PR URL it tracks; --tag comma-separated tags.
    -list      print every ticket in this repo, or with SPEC (an id, range,
               list or description regex) each matching ticket's whole record (--workspace, or outside any
               repo: every repo under ~/git, repo first); --open/--closed filter
    -advance   move one ticket one legal step forward in idea->footgun<->dogfood:
               idea to footgun, footgun to dogfood.
               --why records the evidence (the footgun named, the dogfood
               run) in stage_history
    -back      dogfood back to footgun, the other half of footgun<->dogfood:
               real use found something. --why is required
    -close     close tickets by id, range, or description regex; --why
               records the evidence as closed_reason -- a closed ticket with
               no reason is a claim, one with a reason is a record
    -html      render the tickets as the body of a todo page: a stats strip
               and two cards (open, done -- struck through), rows carrying
               stage, repo, source and ref as pills, in the org's card markup
               (data-tc-collapse, data-tc-arrange, data-tc-table) so the
               shared library/js components work on it. --workspace renders
               every repo under DIR (default ~/git) that has .hee/tickets,
               which is what "one todo.html" means. Prints to stdout, or
               --out FILE. Real trigger (2026-09-10, operator): "take all the
               old todo's ... cross off all those that are done. let's use
               our own hee ticket system for this. I just want one todo.html".
    -json      every ticket as one JSON document, each with its flow judged
               (CRITICAL: unreadable, unknown stage, illegal move; WARNING:
               a move with no why, a close with no reason). --workspace as
               for -list. What hee check tickets and hee view --tickets read.

    Exactly one action runs per invocation. If several are passed they are
    tested in the order above and the first one present wins; the rest are
    silently ignored rather than rejected.

    Add `help` after any action for its own page:
        hee-ticket -close help
