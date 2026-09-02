% HEE-DNS(1) | HEE Tools

# NAME

hee-dns - generate BIND zones from one flat host file.

# SYNOPSIS

    hee-dns generate HOSTFILE --out DIR
    hee-dns check HOSTFILE
    hee-dns help | --help | -h


# DESCRIPTION


    hee-dns generate HOSTFILE [--out DIR]   write forward + reverse zones
    hee-dns check    HOSTFILE               parse and report, write nothing
    hee-dns help                            this page


# EXIT STATUS

    0   the host file parsed; zones written (generate) or reported (check)
    1   usage error -- unknown subcommand, or generate without --out
    2   the host file has a malformed record; nothing was written

    A duplicate-PTR warning does NOT change the exit status. It is a
    judgement call, not a parse error: two `=` records on one address is
    legal and occasionally deliberate.

# WHY THIS EXISTS


    lab.tcos.us had sixteen A records and zero PTR records. Not through
    neglect -- through structure. BIND wants a forward zone and a separate
    reverse zone, both maintained by hand, and the second one loses. Spencer,
    2026-09-02: "make forward, make backward too (unless reason)".

    So the rule is encoded in the source rather than remembered. The host file
    is tinydns's format, whose first character says which directions a record
    gets:

        =name:ip:ttl    A and PTR      -- a real machine
        +name:ip:ttl    A only         -- a vhost on a shared proxy
        @zone::mx:dist:ttl             -- MX

    "Unless reason" is the `+`. Eight names in this lab point at haproxy; an
    address gets ONE PTR naming the machine, not every vhost it fronts.

    The format was chosen for a second reason: it is already djbdns-native. If
    this lab ever swaps BIND for tinydns the source file is the input, not a
    migration.

    SERIAL NUMBERS are YYYYMMDDnn, bumped against whatever is already deployed
    so a regeneration on the same day does not go backwards -- a stale serial
    is silently ignored by secondaries, which is the classic way a zone update
    "succeeds" and changes nothing.
