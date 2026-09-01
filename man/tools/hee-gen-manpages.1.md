% HEE-GEN-MANPAGES(1) | HEE Tools

# NAME

hee-gen-manpages - generate man pages from each tool's own --help

# SYNOPSIS

    hee-gen-manpages                     dry run: report what would change
    hee-gen-manpages --write             write the pages
    hee-gen-manpages --gopher [DIR]      dry run of the published gopher tree
    hee-gen-manpages --gopher --write    build it
    hee-gen-manpages help


# DESCRIPTION


    Extracts each tool's own --help output and renders it as a man page. No
    page is hand-authored here; the tool's help IS the page, per rule 17.

    DRY RUN IS THE DEFAULT. With no arguments this writes nothing at all --
    it generates into a temporary directory, compares that against what is
    committed, and prints the difference. Add --write to apply it.

    Operator, 2026-09-01: "I don't like that it just writes files when you
    run it without args. those file need to go to a certain spot and oper
    needs to know that." The precedent is real and already cost something:
    a bare run of this tool was once observed installing a pre-commit hook
    as a side effect of generating documentation (issue:464@human-execution-engine),
    which is why library/py/hee_toolver never invokes a tool without a flag.


# OPTIONS

    --write        apply the changes. Without it nothing is written.
    --gopher [DIR] render the published gopher tree. DIR defaults to
                   man/gopher. Rebuilt from scratch, so with --write this
                   REMOVES the existing tree first.


# EXIT STATUS

    0 OK   1 nothing generated, or an unknown argument

# DESTINATIONS

    Both are inside the repo that owns the TOOL, never the current
    directory -- this tool resolves its own location first. The absolute
    path is printed on every run, dry or not.

      man/tools/           generated pages, .N.md sources and manN/*.N roff
      man/tools/README.md  the index
      man/gopher/          --gopher only: the tree man.tcos.us serves

    man/manN/ holds pages written BY HAND. Those WIN: generation skips any
    tool with an authored page and says so.
