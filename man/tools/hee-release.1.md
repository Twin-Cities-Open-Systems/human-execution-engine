% HEE-RELEASE(1) | HEE Tools

# NAME

hee-release - lab, cut, promote: releases for one repo, a list, or the org

# SYNOPSIS

      hee release -status  [SELECT]                what main holds beyond the last release, per surface
      hee release -next    [SELECT]                the version the next cut gets (semver from the commits)
      hee release -find    [SELECT]                releases that exist, with dates and surfaces
      hee release -lab     [SELECT]                build and push every surface to lab, gates included
      hee release -cut     [SELECT] [-version vX.Y.Z] [-yes]   build, changelog, release commit + PR
      hee release -promote [SELECT] [-yes]         every surface from the release commit, tagged, published
      hee release -publish [SELECT] [-version vX.Y.Z] [-yes]   the GitHub Release for an existing version tag
      hee release -requires [SELECT]               what lab, cut and promote need on this machine; checks only
      hee release help

      SELECT picks repos. Nothing: the repo you are in. -all: every checkout
      under ~/git with a release card. -repos REGEX[,REGEX]: anchored regular
      expressions over checkout names ('tcos-.*', 'resume|hee'; hee, gh, www
      are aliases). -where "EXPR": a small SQL-like filter over what the repo
      or release IS (below). Flags take one dash like the rest of hee (two
      are accepted). Anything that writes is a dry run until -yes.

    REGEX OR GLOB -- WHICH, WHERE
      Regex wherever feasible; a glob only where the flag says glob.
        -repos            REGEX, anchored (fullmatch). 'tcos-.*' not 'tcos-*'.
        -where  f ~ 'x'   REGEX, searched anywhere in the value.
        -where  f like 'x'  GLOB (* ? [..]), the one glob in the tool, for people who think in shells.
        -where  f = 'x'   exact; < <= > >= semver-aware for versions.
      Names given without regex metacharacters are validated against the
      regex registry's org-repo-name (library/regex/patterns.yaml) before
      anything runs, so a path or a typo never reaches git or gh.


# DESCRIPTION


    The release procedure was a dozen commands across three scripts, each
    with its own timestamp tag. This is the whole procedure now, from any
    directory:

      hee release -lab -repos hee              review on lab
      hee release -cut -repos hee -yes         builds every surface into the release commit, opens the
                                               release PR; approving and merging it IS the sign-off (HEE_POLICY 17)
      hee release -promote -repos hee -yes     every surface, one version, verified, published

    A repo declares its surfaces in release.card.v1.yaml at its root:

      apiVersion: hee/v1
      kind: Card
      metadata: { name: tcos-www-release, labels: { domain: release } }
      spec:
        credential: { account: cloudflare-tcos-www, dir: .hee/secrets }   # optional: promote runs under hee cred
        build: "./convert.sh"            # optional, repo-level: one build renders every surface (resume)
        outputs: ["media", "dist"]       # its tracked outputs
        surfaces:
          - name: tcos-www
            build: "python3 generate-public-site.py"     # optional: run by cut, outputs go into the release commit
            outputs: ["*.html", "!*.template.html"]       # git pathspecs (glob); a leading ! excludes
            lab: "./deploy.sh lab"
            promote: "./deploy.sh promote"

    Each surface's promote receives RELEASE_VERSION and tags
    prod/<surface>/<version>; the tool then signs <version> on the release
    commit (hee git tag) and publishes the GitHub Release, notes being that
    version's CHANGELOG section.


# FILES

    release.card.v1.yaml         the repo's surfaces and credential (repo root)
    CHANGELOG.md                 written by cut, read by promote
    library/regex/patterns.yaml  org-repo-name, the validation pattern for -repos


# EXIT STATUS

    0 OK, 1 WARNING (nothing to release, nothing selected), 2 CRITICAL (gate, build or deploy failed, bad name or regex),
    3 UNKNOWN (no card, or a requirement the card declares is missing)


# SEE ALSO

    hee-gen-changelog(1), hee-git-tag(1), hee-git-merge(1), hee-cred(1), hee-fields(1)

# REQUIREMENTS

      A card can declare what its steps need on the machine that runs them.
      -lab, -cut and -promote check it FIRST, before any build or deploy, and
      report every missing item at once as UNKNOWN (3), each naming the step
      and surface that needs it. -requires runs the checks alone, for all
      three steps, and builds nothing.

        spec:
          requires:                          # every step
            commands: [git, python3, exiftool]
            python: [PIL, yaml]              # python3 -c "import PIL"
            files: [../fleet-ops/tools/meme-factory/tile/tile.py]   # repo-relative; ~ allowed
            lab: { ssh: [pve] }              # ssh -o BatchMode=yes HOST true
            cut: { commands: [gh] }
            promote:                         # this step only
              versions: { node: ">=20" }     # the first version in `node --version`
              decrypt: [../tcos-www/.hee/secrets/cloudflare-tcos-www.gpg]
          surfaces:
            - { name: web, requires: { commands: [wrangler] }, lab: "./deploy.sh lab", promote: "./deploy.sh promote" }

      A surface's requires has the same shape. decrypt reads the sealed file's
      recipient key ids and looks for a matching secret key (gpg
      --list-secret-keys); it never decrypts. A card's credential: adds its
      sealed file to promote's files and decrypt checks. A card without
      requires runs exactly as before. The one install hint is the Python
      package behind a module whose name differs (PIL is Pillow); distro
      package names differ per distro and are never guessed.

      Operator, 2026-09-12, after a promote on a fresh machine failed one
      missing dependency at a time: "why is it just crashing, should be taken
      care of already" (human-execution-engine#729).

    THE -where LANGUAGE
      field op value, joined by and / or, parentheses allowed. Fields:

        repo       checkout name                    surface   any surface name
        cur_ver    last v* tag, or unreleased       ahead     commits since it
        next_ver   what the next cut would be       bump      first|patch|minor|major
        ver, date  a release tag and its date (-find only)

        hee release -status -where "cur_ver ~ '^v1\.[12]\.' and bump = minor"
        hee release -find -all -where "ver >= v1.0.0 and date >= 2026-09-01"
        hee release -promote -repos 'tcos-.*|resume' -where "ahead > 0" -yes

      The fields are a schema and probe() is its one backend today (git and
      the release card). The same expression is meant to reach tickets
      (hee fields) and an on-prem git remote next: same words, more backends,
      the objects we already keep and their metadata -- rich and dead simple.


# VERSIONS

    Semantic. The next version comes from the Conventional Commit subjects
    merged since the last v* tag: a `!` or BREAKING CHANGE bumps major,
    feat bumps minor, anything else bumps patch. No v* tag yet: v1.0.0,
    because prod is already real. -version overrides.

    cut runs each surface's build and stages its outputs, writes
    CHANGELOG.md through hee gen-changelog --release, commits
    "chore(release): vX.Y.Z" on release/vX.Y.Z, pushes, opens the PR: the
    PR shows the exact bytes that ship (hee#594). Without -yes it builds,
    lists what the commit would carry, and restores the tree. promote
    refuses unless HEAD is origin/main and CHANGELOG's newest header is
    the version; without -yes it prints the plan and runs nothing.
