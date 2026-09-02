% HEE-NAME(1) | HEE Tools

# NAME

hee-name - hee-name command

# SYNOPSIS

    hee-name [-h] [-list-pools] [-allocate] [-release NAME] [-list]

# DESCRIPTION

                    [--pool POOL] [--scope SCOPE] [--prefix PREFIX]
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
      --cohabit INSTANCE    deliberately share an EXISTING instance rather than
                            taking a fresh one
      --role ROLE           role suffix; required for scopes in
                            ROLE_REQUIRED_SCOPES
      --allocations-dir PATH
                            anchor the ledger here (else $HEE_NAME_ALLOCATIONS,
                            else this tool's repo)
