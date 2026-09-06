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

    hee git tag prod/tcos-www/20260906T0806Z -m "prod promotion: tcos.us" e7beec0 --yes --push
    hee git tag --show-key


# SEE ALSO

    hee-git-merge(1), hee-ver(1), hee-contract-review(1)

# KEY SELECTION

    1. --key ID, if given (any form gpg accepts).
    2. Otherwise the secret keys in the caller's own keyring that can sign,
       are not expired or revoked, and carry ultimate trust (the keys this
       person generated here, as opposed to imported ones).
    3. If more than one remains, the one whose uid email host is this
       machine per the SOA anchor (~/.hee/index/_.yaml `host:`), e.g.
       spencer@kiosk.lab.tcos.us on kiosk.lab.tcos.us.
    4. Still more than one, or none: CRITICAL with the candidates listed --
       say --key. Never a guess.

    Nothing is read from gitconfig. The chosen key id is printed on every
    run so the record says which key signed.
