% HEE-MAIL(8) | HEE Tools

# NAME

hee-mail - mailboxes, aliases and master access on the fleet's mail exchanger

# SYNOPSIS

    hee mail list
    hee mail add     NAME[@DOMAIN] -recipients KEYID[,KEYID...]
    hee mail passwd  NAME[@DOMAIN] -recipients KEYID[,KEYID...]
    hee mail alias   ADDR TARGET
    hee mail unalias ADDR
    hee mail master  NAME[@DOMAIN]
    hee mail unmaster NAME[@DOMAIN]
    hee mail record  [-write]
    hee mail check   [DOMAIN]
    hee mail help


# DESCRIPTION


    One mailbox is three things that must agree: a row in the mail host's
    virtual table (where the address goes), a credential in two files on that
    host (smtpd for submission, dovecot for IMAP), and a sealed password
    someone can actually open. This tool keeps them in step; doing it by hand
    is how a password works on 587 and not on 993.

    The mail host is named by a package directory -- the fleet-ops
    hosts/<mx>/ tree that carries droplet.conf (its address), known_hosts
    (its pinned key) and tables/ (its domains and virtuals). Default:
    ~/git/fleet-ops/hosts/mx1-tcosagent-com, or $HEE_MAIL_PKG.

    add generates a password with hee-pwgen, seals it to -recipients as
    mail-<name> in the package repo's .hee/secrets, hashes it ON the mail
    host with `smtpctl encrypt`, writes that hash to both credential files,
    and creates the Maildir owned by vmail. The plaintext is held in one
    shell variable, handed to gpg and to ssh on stdin, and never printed,
    never in argv, never in a file. passwd is the same thing for an address
    that already exists -- a rotation.

    Seal to every key that has a real reason to open it: the mailbox owner's
    personal key AND the per-host key of each machine they read mail from
    (HEE_POLICY §24). A password sealed only to a key that lives on another
    machine is a password nobody can use where they are.

    master makes an account a dovecot master user: it then opens any mailbox
    as "<mailbox>*<master>" with its own password, and dovecot logs every
    such login. No password is generated or changed, and nothing is copied.
    This is how an operator reads the fleet's mail without holding anyone
    else's credential.

    record renders the mailbox list as YAML under the package's repo
    (mail/accounts.<domain>.yaml). It holds addresses, kinds and recipients
    -- never a password or a hash. inv.lab already syncs fleet-ops, so the
    record is how mail identities reach the inventory rather than a second
    API to keep alive.


# OPTIONS

    -recipients IDS   with add/passwd: GPG key ids or emails, comma separated
    -pkg DIR          the mail host package (default: $HEE_MAIL_PKG, else
                      ~/git/fleet-ops/hosts/mx1-tcosagent-com)
    -target root@HOST override the address in the package's droplet.conf
    -domain DOMAIN    default domain for a bare NAME (default: tcosagent.com)
    -write            with record: write the file (default prints it)
    -dry-run          with add/passwd: run every check, change nothing


# EXIT STATUS

    Nagios plugin convention.
    0 OK   1 WARNING   2 CRITICAL   3 UNKNOWN (usage)

# EXAMPLES

    $ hee mail help                                          # ci
    $ hee mail list
    $ hee mail add spencer -recipients 18602F28834DBB05,01C9F82A7582A4DC
    $ hee mail alias postmaster@tcosagent.com spencer@tcosagent.com
    $ hee mail master spencer
    $ hee mail record -write
