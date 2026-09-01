% HEE-GEN-MANPAGES(1) | HEE Tools

# NAME

hee-gen-manpages - generate man/tools/*.N.md and manN/*.N from each tool's --help

# SYNOPSIS

    hee-gen-manpages


# DESCRIPTION


    No arguments. Re-run after any tool change.

    Writes into the repo that owns the TOOL, never the current
    directory: it resolves its own location and writes to
    <tool-repo>/man/tools.

    The resolved absolute path is printed when it RUNS, not here --
    help output is captured verbatim into the generated man page, so
    a machine-specific path in help becomes a machine-specific path
    in checked-in documentation (fleet-ops#352).

    Each page is generated FROM the --help output of each tool, so
    tool help text is what becomes its man page.


# EXIT STATUS

    0 OK   1 nothing generated
