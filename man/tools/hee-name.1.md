% HEE-NAME(1) | HEE Tools

# NAME

hee-name - DEPRECATED, being phased out: do not name anything from a pool

# SYNOPSIS

    hee-name [-h] [-list-pools] [-allocate] [-release NAME] [-list]

# DESCRIPTION

                    [--pool POOL] [--scope SCOPE] [--prefix PREFIX] [--durable]
                    [--cohabit INSTANCE] [--role ROLE] [--allocations-dir PATH]

    DEPRECATED, being phased out: do not name anything from a pool.

    Name things for what they are and do -- a short 1-3 word phrase plus a
    number: haproxy-1, nginx-3, shell-1. Always numbered, even the first one;
    never zero-padded. Operator, 2026-09-30 and 2026-10-01: "we name things based
    on what they are and what they do, not names I don't know how to spell." This
    is the interim rule until a naming standard exists (fleet-ops pve/GUIDE.md,
    "Deploy a new container", step 2).

    -allocate refuses (exit 2) unless HEE_NAME_ALLOW_DEPRECATED=1 is set.
    -list, -list-pools and -release still work, to wind existing allocations
    down. Names already in service are not renamed by this.

    options:
      -h, --help            show this help message and exit
      -list-pools
      -allocate
      -release NAME
      -list
      --pool POOL
      --scope SCOPE
      --prefix PREFIX
      --durable             allocate the permanent singleton bast-<role>, not a
                            pool name
      --cohabit INSTANCE    deliberately share an EXISTING instance rather than
                            taking a fresh one
      --role ROLE           role suffix; required for scopes in
                            ROLE_REQUIRED_SCOPES
      --allocations-dir PATH
                            anchor the ledger here (else $HEE_NAME_ALLOCATIONS,
                            else this tool's repo)


# EXAMPLES

    $ hee name -list-pools --allocations-dir "$(mktemp -d)"   # ci
    $ hee name -allocate --pool simpsons --allocations-dir "$(mktemp -d)" || test $? -eq 2   # ci

    The first reads the bundled pool config and writes nothing. The second
    proves -allocate refuses with exit 2 while the tool is deprecated. -release
    mutates the allocations directory and is left unmarked.
