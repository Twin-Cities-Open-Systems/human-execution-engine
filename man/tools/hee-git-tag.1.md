% HEE-GIT-TAG(1) | HEE Tools

# NAME

hee-git-tag - a GPG-signed git tag with the key that is really yours

# SYNOPSIS

    hee git tag NAME -m MESSAGE [COMMIT] [--key ID] [--push] [--yes]
    hee git tag --show-key
    hee git tag help


# DESCRIPTION


    Creates an annotated, GPG-signed tag (`git tag -s`) and, with --push,
    pushes exactly that ref. The point of the tool is the key choice: plain
    `git tag -s` asks gpg for a key whose uid matches user.email, and in this
    org user.email is the shared dev@tcos.us from the dotfiles gitconfig --
    no secret key carries that uid, so the first prod promote ended with
    "gpg: skipped Spencer Butler <dev@tcos.us>: No secret key" (2026-09-06).

    Dry run by default: prints the key, the tag, the commit and the message
    and changes nothing. --yes creates the tag; --push pushes it.


# FILES

    ~/.hee/index/_.yaml    SOA anchor; only `host:` is read, for the tie-break


# EXIT STATUS

    0 OK, 2 CRITICAL (no key, ambiguous key, git or gpg failed), 3 UNKNOWN
    (gpg missing, not a git repo).


# EXAMPLES

    hee git tag --show-key
    hee git tag v1.2.0 -m "release 1.2.0" --push

    Not marked "# ci": --show-key needs a signing key configured (a CI runner
    has none) and tagging signs and pushes. Both are host/identity state, not
    a self-contained run.

    hee git tag prod/tcos-www/20260906T0806Z -m "prod promotion: tcos.us" e7beec0 --yes --push
    hee git tag --show-key


# SEE ALSO

    hee-git-merge(1), hee-ver(1), hee-contract-review(1)

# KEY SELECTION

    1. --key ID, if given (any form gpg accepts).
    2. Otherwise $HEE_SIGN_KEY, if set. This is how `hee release -promote`,
       which calls this tool itself, is told which key to use when the
       keyring holds several: HEE_SIGN_KEY=<id> hee release -promote -yes.
       Never a default -- unset means step 3.
    3. Otherwise gpg's own `default-key` from gpg.conf (read with
       `gpgconf --list-options gpg`; gpg has no switch that prints it), if it
       names a usable secret key here -- the last one that does, as gpg
       itself picks. This is the one place to say "my signing key" for both
       gpg and hee: `default-key 2A361A96A7A0FBA9` in ~/.gnupg/gpg.conf.
    4. Otherwise the secret keys in the caller's own keyring that can sign,
       are not expired or revoked, and carry ultimate trust (the keys this
       person generated here, as opposed to imported ones).
    5. If more than one remains, the one whose uid email host is this
       machine per the SOA anchor (~/.hee/index/_.yaml `host:`), e.g.
       spencer@kiosk.lab.tcos.us on kiosk.lab.tcos.us.
    6. Still more than one, or none: CRITICAL with the candidates listed --
       say --key (or set HEE_SIGN_KEY). Never a guess.

    Nothing is read from gitconfig. The chosen key id is printed on every
    run so the record says which key signed.
