% HEE-COMPLETION(1) | HEE Tools

# NAME

hee-completion - bash completion for hee that teaches while it completes

# SYNOPSIS

    hee completion bash                  print the bash completion script (source it, or install it)
    hee completion -words WORD...        candidates for the next word, then a hint table (the script calls this)
    hee completion install               write ~/.local/share/bash-completion/completions/hee
    hee completion help


# DESCRIPTION


    Every hee tool documents itself in its --help, the man pages are
    generated from that help (hee gen-manpages), and so is this: the
    candidates for the next word and the one-line meaning of each come from
    the same SYNOPSIS and SUBCOMMANDS text, read live and cached by the
    tool's mtime. Nothing is typed twice, nothing goes stale on its own.

    Two TABs show the hint table above the prompt:

      $ hee release -<TAB><TAB>
        -status    what main holds beyond the last release, per surface
        -cut       build, changelog, release commit + PR
        -promote   every surface from the release commit, tagged, published
        ...

    That is the point: a completion is a learning tool as much as a saving
    of keystrokes (operator, 2026-09-06: "guide the human opers to the
    possible next args ... a learning tool as much as a carpal tunnel
    strategy"). Completions are standard, not optional: dotfiles installs
    and loads them for every oper.


# FILES

    ~/.cache/hee/completion/*.json                       per-tool cache, invalidated by the tool's mtime
    ~/.local/share/bash-completion/completions/hee       what `install` writes; dotfiles' .bashrc loads it


# EXIT STATUS

    Nagios plugin convention, like every other hee tool.
    0 OK        the script printed, the file installed, or candidates emitted
    2 CRITICAL  unrecognized argument
    3 UNKNOWN   reserved

    `-words` exits 0 even when it has nothing to suggest. At the prompt a
    failed completion and a completion with no candidates look identical, and
    bash discards the exit code either way -- so it reports success and prints
    nothing rather than a status nobody can observe.


# SEE ALSO

    hee-gen-manpages(1), hee-check(1) (cli: every tool's help obeys the contract)

# WHAT COMPLETES

    hee <TAB>              every tool under tooling/bin/hee-* plus the dispatcher's
                           families (git merge|tag, hooks install, ...), each with its NAME line
    hee TOOL <TAB>         the tool's subcommands and flags from its SYNOPSIS; -word and
                           --word forms as the tool spells them
    hee TOOL SUB <TAB>     flags that appear on that subcommand's SYNOPSIS line
    paths                  when the SYNOPSIS says PATH, FILE or DIR at that position, files complete
