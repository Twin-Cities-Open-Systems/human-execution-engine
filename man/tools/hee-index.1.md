% HEE-INDEX(1) | HEE Tools

# NAME

hee-index - generate hee/INDEX.md, the persisted index of every HEE object

# SYNOPSIS

    hee-index [--out FILE]
    hee-index help


# DESCRIPTION


    Walks every HEE object (apiVersion: hee/v1) in the current repo, groups
    them by kind, and writes an index carrying each object's live pass/fail
    compliance status.

    A thin wrapper around hee-lint's own scan -- it reuses that pass/fail
    logic rather than parsing YAML a second time, so there is one
    implementation of "is this object valid", not two.

      --out   where to write the index. Default: hee/INDEX.md

    The output is generated state and is checked for staleness in CI; run
    this and commit the result whenever objects change.


# EXIT STATUS

    0 written   1 unknown argument   2 not in a git repo
