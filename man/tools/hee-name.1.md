% HEE-NAME(1) | HEE Tools

# NAME

hee-name - hee-name command

# SYNOPSIS

    hee-name [-h] [-list-pools] [-allocate] [-release NAME] [-list]

# DESCRIPTION

                    [--pool POOL] [--scope SCOPE] [--prefix PREFIX] [--durable]
                    [--cohabit INSTANCE] [--role ROLE] [--allocations-dir PATH]

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

    -list-pools reads the bundled pool config and writes nothing, so it is
    proven in CI over a scratch allocations dir. -allocate and -release mutate
    the allocations directory and are left unmarked.
