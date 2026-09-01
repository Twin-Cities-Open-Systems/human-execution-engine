% HEE-TOOLS(1) | HEE Tools

# NAME

hee-tools - router for the external-toolchain check/update pair

# SYNOPSIS

    hee-tools [check] [MANIFEST]
    hee-tools update [MANIFEST] [EVIDENCE_DIR]
    hee-tools [SUBCOMMAND] help


# DESCRIPTION


    A two-line router. It does no work of its own: it execs one of two
    sibling scripts in the same directory and passes every remaining
    argument through unchanged.

    With no subcommand it runs `check`, so a bare `hee-tools` is a
    read-only inventory of the external tools this org expects to find on
    a machine. Nothing is installed unless `update` is asked for by name.


# SUBCOMMANDS

    check    report presence + version of every tool in the manifest
             (default; execs hee-tools-check)
    update   install/refresh the tools the manifest pins a version for
             (execs hee-tools-update)

    Add `help` after either for its own page:
        hee-tools update help


# EXIT STATUS

    Nagios plugin convention.
    0 OK        the subcommand exited 0
    2 CRITICAL  unknown subcommand (usage printed to stderr)

    Any other status is the subcommand's own -- this router execs, so it
    never rewrites the exit code of the tool it hands off to.


# SEE ALSO

    hee-tools-check, hee-tools-update, tooling/tools.manifest.txt
