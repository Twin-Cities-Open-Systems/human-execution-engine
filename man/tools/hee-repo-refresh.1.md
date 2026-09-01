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


# SCOPE

    A bare REPO_DIR is a filesystem path and is what bootstrap.mk passes
    internally; it skips the governance reminder, since that form is always
    one worker among many. `all`/`-all` and `-repo NAME,NAME` are the
    human-facing forms, and take repo NAMES (dotfiles, not a full path),
    resolved under ${HEE_GIT_ROOT:-$HOME/git}.
