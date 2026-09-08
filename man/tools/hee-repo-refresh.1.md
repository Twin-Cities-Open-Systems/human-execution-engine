% HEE-REPO-REFRESH(1) | HEE Tools

# NAME

hee-repo-refresh - per-repo health check, pull, hygiene and branch prune

# SYNOPSIS

    hee-repo-refresh MODE REPO_DIR
    hee-repo-refresh MODE [all|-all]
    hee-repo-refresh MODE -repo NAME[,NAME...]
    hee-repo-refresh help


# DESCRIPTION


    The worker behind bootstrap.mk's health-all-repos and pull-all-repos
    targets. It lives in its own script, not inline in the Makefile, so the
    GNU parallel path and the sequential fallback call the same logic rather
    than two copies that can drift.


# ENVIRONMENT

    HEE_GIT_ROOT   where repos live. Default: $HOME/git


# EXIT STATUS

    0 completed   2 usage error

# MODES

    health    report each repo's state in one line
    pull      fast-forward each repo
    hygiene   dirty-file and no-upstream-branch counts across ALL local
              branches; prints nothing at all for a clean repo
    prune     delete local branches GitHub confirms are merged
    refresh   health, then pull, then the governance reminder -- the same
              sequence as bootstrap.mk's refresh-all-repos
    gate      does this repo still pass hee-check as its own CI runs it,
              against the human-execution-engine checkout beside it? The same
              question .github/workflows/stable.yaml asks in CI before letting
              `stable` advance -- asked locally, before pushing a tightening
              that would turn other repos red with no commit to them


# SCOPE

    A bare REPO_DIR is a filesystem path and is what bootstrap.mk passes
    internally; it skips the governance reminder, since that form is always
    one worker among many. `all`/`-all` and `-repo NAME,NAME` are the
    human-facing forms, and take repo NAMES (dotfiles, not a full path),
    resolved under ${HEE_GIT_ROOT:-$HOME/git}.


# GATE

    Runs `hee-check all .` from INSIDE each repo, with human-execution-engine
    as a sibling checkout. Both details are load-bearing and were each measured
    wrong first: hee-check resolves cross-repo references by walking sibling
    checkouts with git, so an absolute-path invocation from elsewhere reports
    CRITICAL that the repo's own CI never sees.

    A repo's own HEE_*_SKIP exemptions are read out of its workflows and
    replayed, because "the repo declares the exemption, the checker never
    guesses". Reading them from the repo beats copying them: a copy drifts.

    A result is annotated when the tree is not a clean main at origin --
    [on BRANCH, not main], [N behind origin], [N uncommitted]. An unannotated
    line is the only one that is an answer about main.

    It judges the WORKING TREE, not origin. That is the point locally -- you
    want to know before you push -- but it means a result here can differ from
    CI. Measured 2026-09-07: dotfiles read 2 findings locally and 0 from a
    clean clone, purely from uncommitted work. When the two disagree, CI is
    right about main and this is right about your desk.

    Exit is 0 even when repos fail -- this reports, it does not gate. Read the
    per-repo lines.
