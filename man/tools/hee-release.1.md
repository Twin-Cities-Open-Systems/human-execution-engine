% HEE-RELEASE(1) | HEE Tools

# NAME

hee-release - lab, cut, promote: a repo's release in three commands

# SYNOPSIS

    hee release status            what main holds beyond the last release, per surface
    hee release next              the version the next cut gets (semver from the commits)
    hee release lab               build and push every surface to lab, gates included
    hee release cut [VERSION]     changelog + version commit on a release branch, as a PR
    hee release promote           deploy every surface from the release commit, tag it, publish it
    hee release publish [VERSION] the GitHub Release for an existing version tag, notes from CHANGELOG.md
    hee release help


# DESCRIPTION


    The release procedure was a dozen commands across three scripts, each
    with its own timestamp tag (operator, 2026-09-06: "way too much to do
    ... trimming that down and getting tags working properly and semver").
    This is the whole procedure now:

      hee release lab        review on lab
      hee release cut        approve and merge the release PR -- that IS the sign-off (HEE_POLICY 17)
      hee release promote    every surface, one version, verified

    A repo declares its surfaces in release.card.v1.yaml at its root:

      apiVersion: hee/v1
      kind: Card
      metadata: { name: tcos-www-release, labels: { domain: release } }
      spec:
        credential: { account: cloudflare-tcos-www, dir: .hee/secrets }   # optional: promote runs under hee cred
        surfaces:
          - { name: tcos-www, lab: "./deploy.sh lab", promote: "./deploy.sh promote" }

    Each surface's promote command receives RELEASE_VERSION in its
    environment and tags prod/<surface>/<version>; the tool then signs
    <version> itself on the release commit (hee git tag) and publishes the
    GitHub Release for it, notes being that version's CHANGELOG section
    (operator, 2026-09-06: "where is 1.0.0 release info" -- the first
    releases were tags only). Timestamps are gone from tag names; they
    live in the tag's own date.


# FILES

    release.card.v1.yaml    the repo's surfaces and credential (repo root)
    CHANGELOG.md            written by cut, read by promote


# EXIT STATUS

    0 OK, 1 WARNING (nothing to release), 2 CRITICAL (gate, build or deploy failed), 3 UNKNOWN (no card)


# SEE ALSO

    hee-gen-changelog(1), hee-git-tag(1), hee-git-merge(1), hee-cred(1)

# VERSIONS

    Semantic. The next version comes from the Conventional Commit subjects
    merged since the last v* tag: a `!` or BREAKING CHANGE bumps major,
    feat bumps minor, anything else bumps patch. No v* tag yet: v1.0.0,
    because prod is already real. `cut VERSION` overrides.

    cut writes CHANGELOG.md through hee gen-changelog --release, commits
    "chore(release): vX.Y.Z" on release/vX.Y.Z, pushes, opens the PR. The
    approval on that PR is the human sign-off; promote refuses unless HEAD
    is origin/main and its CHANGELOG's newest header is the version.
