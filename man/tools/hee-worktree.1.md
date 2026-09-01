% HEE-WORKTREE(1) | HEE Tools

# NAME

hee-worktree - per-session git worktree, no extra clone

# SYNOPSIS

    hee-worktree start BRANCH [--from BASE]
    hee-worktree list
    hee-worktree done BRANCH
    hee-worktree [SUBCOMMAND] help


# DESCRIPTION


    Gives each concurrent session its own checked-out directory instead of
    every session fighting over one HEAD. A git worktree shares the same
    .git/objects store as the main clone, so a second branch costs working
    files only, not a second copy of the history.

    Path convention, and the whole point of the tool being a tool rather
    than a habit:

        <repo-root>.worktrees/<branch-with-unsafe-chars-replaced-by->

    A sibling of the repo root, deliberately NOT nested inside the tracked
    tree, so it can never confuse `git ls-files` or `git status` in the
    main clone. Every character outside [A-Za-z0-9._-] in the branch name
    becomes a hyphen, so two branches differing only in those characters
    would collide on one directory.

    The repo root is resolved from the CURRENT directory, so where you run
    this from decides which repo gets the worktree.


# SUBCOMMANDS

    start   create or reuse a worktree, print its path
    list    git worktree list, as-is
    done    remove the worktree; the branch itself is untouched

    Add `help` after any subcommand for its own page:
        hee-worktree start help


# ENVIRONMENT

    No environment variables are read. `git` must be on PATH and the
    current directory must be inside a git repo.


# EXIT STATUS

    Nagios plugin convention.
    0 OK        the subcommand did its job
    1 WARNING   not in a git repo, git refused the operation, or no
                subcommand was given (this page is printed). Note: the org
                vocabulary would put these at 2 CRITICAL / 3 UNKNOWN; the
                tool really exits 1 today and is documented as-is, not
                changed here.


# SEE ALSO

    git-worktree(1)
