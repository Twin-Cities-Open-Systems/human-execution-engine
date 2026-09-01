% HEE-HG(1) | HEE Tools

# NAME

hee-hg - launcher for the Hunter-Gatherer orchestrator (LIBRARY MISSING)

# SYNOPSIS

    hee-hg [ARGUMENTS...]
    hee-hg help


# DESCRIPTION


    A thin launcher, and nothing more. It puts tooling/hee-hg/lib on
    sys.path, imports `cli`, and calls cli.main(), which parses every
    argument itself.

    THAT LIBRARY IS NOT IN THIS REPOSITORY. tooling/hee-hg/lib/ does not
    exist on disk and git history has no record of it ever being added or
    removed here, so as shipped this script cannot run: any invocation
    prints an import error naming the missing module and the paths it
    searched, then exits 1.

    Consequently no synopsis, no options and no exit codes beyond that one
    can be documented honestly. The only description of intent that exists
    is the script's own docstring: "HEE Hunter-Gatherer: Pill-based patch
    discovery and application orchestrator." What a "pill" is here, what
    subcommands exist, and what the tool does to a repository are all
    unknown from this repository alone. Restore or vendor the library and
    this page can be replaced with a real one.


# ENVIRONMENT

    Unknown -- whatever the missing cli module reads.

# FILES

    tooling/hee-hg/lib/cli.py   required, and absent from this repository


# EXIT STATUS

    Nagios plugin convention.
    0 OK   this help was printed
    1      the `cli` module could not be imported -- the current state of
           every real invocation. Note: an unusable dependency is
           3 UNKNOWN in the org vocabulary; the launcher really exits 1
           today and is documented as-is, not changed here.
    Any other status comes from cli.main(), which is not present to inspect.
