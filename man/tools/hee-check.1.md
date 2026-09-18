% HEE-CHECK(1) | HEE Tools

# NAME

hee-check - repo boundary and integrity checks

# SYNOPSIS

    hee-check [boundary] [PATH]
    hee-check refs [--fix] [PATH]
    hee-check systemd [PATH]
    hee-check locale [PATH]
    hee-check cli [TOOLDIR] [--json] [--quiet]
    hee-check regex
    hee-check signatures [PATH] [--re-sign --key GPG-KEY-ID]
    hee-check all [PATH]
    hee-check [SUBCOMMAND] help


# DESCRIPTION


    Checks a repository for integrity problems. PATH defaults to the current
    directory, so the tool checks where it is invoked, never the repo it
    happens to be installed in.

    If PATH holds repositories rather than being one (for example ~/git),
    every repository directly inside is checked and the results totalled.
    One level deep by design -- deeper would crawl vendored checkouts.


# SUBCOMMANDS

    boundary   generated state is not committed (default)
    refs       every file reference resolves
    systemd    systemd unit files are valid
    locale     authored text matches the locale this repo declares
    cli        every hee tool's own help obeys the CLI contract
    regex      shared regex patterns behave identically in every engine
    roster     roster.json's claims match real accounts and org membership
    gitignore  a fresh clone ignores every baseline secret path (git check-ignore on
               sample paths, not a text match), no negation re-including one,
               no duplicates
    signatures every detached .asc verifies against the file it signs,
               and can re-sign the ones that drifted
    tickets    every .hee/tickets record parses and moves legally through
               idea->footgun<->dogfood
    all        boundary + refs + locale + signatures + tickets + gitignore

    Add `help` after any subcommand for its own page:
        hee-check refs help


# ENVIRONMENT

    HEE_STATUS_STYLE   icon (default), ascii, or plain. See heerc.
    HEE_DERIVED_DIRS   directories treated as generated state. Default: .cursor
    HEE_REFS_SKIP      directories whose references are not judged as canonical,
                       space-separated, e.g. viz-dashboard/public -- a rendered
                       surface holding copies of objects it does not own. Not
                       HEE_DERIVED_DIRS, which means "must not be committed".
                       The repo declares the same list once, for every runner,
                       as check.refs_skip in .hee/config.yaml -- see REPO CONFIG.
    HEE_HOME_PATH_SKIP git pathspecs the home-path scan skips, e.g. ':!hosts/*'
                       for host-pinned scripts and units that name the real
                       user on the real host on purpose. The repo declares the
                       exemption as check.home_path_skip in .hee/config.yaml
                       (see REPO CONFIG); the environment appends to it, and
                       the checker never guesses. For a single deliberate
                       line, prefer the marker
                       hee-check:home-ok -- see `hee-check boundary --help`.


# EXIT STATUS

    Nagios plugin convention.
    0 OK   1 WARNING (reserved)   2 CRITICAL   3 UNKNOWN


# EXAMPLES

    hee-check                     boundary check of the current repo
    hee-check refs                every reference in the current repo
    hee-check refs ~/git          every repo under ~/git
    hee-check refs --fix          repair unambiguous references
    hee-check all ~/git/fleet-ops both checks on one repo
    hee-check signatures          verify every detached signature
    hee-check signatures --re-sign --key inspector@tcos.us
                                  re-sign only the drifted signatures that
                                  this key already made


# SEE ALSO

    hee-lint, hee-index, hee-print

# REPO CONFIG

    A repo declares its exemptions once, in .hee/config.yaml, and every
    runner reads them -- a laptop and CI see the same list:

        check:
          refs_skip:                    # directories, HEE_REFS_SKIP form
            - viz-dashboard/public
          home_path_skip:               # git pathspecs, HEE_HOME_PATH_SKIP form
            - ':!pve/agents/jobs/*/in/*'
          lint_skip:                    # git pathspecs, HEE_LINT_SKIP form
            - ':!viz-dashboard/public/*'

    The environment variables append AFTER the file, so a run can widen a
    skip and cannot silently narrow one. Real trigger, fleet-ops ticket
    0067: the lists lived only in the CI workflow, so the same tree was
    green on GitHub and red on every laptop.
