% HEE-SHELL(1) | HEE Tools

# NAME

hee-shell - ssh into a known TCOS host by alias

# SYNOPSIS

    hee-shell <alias|host> [user]
    hee-shell help | --help | -h


# DESCRIPTION


    Thin wrapper over ssh(1) with TCOS host aliases. It grants no access a key
    does not already have.

    A target that is not a known alias is passed to ssh VERBATIM. Be aware that
    with a DNS search domain configured, a bare word can resolve to a real host
    -- so a typo becomes a real connection attempt, not an error.


# EXIT STATUS

    0  OK        ssh ran (its own exit status is returned)
    3  UNKNOWN   no target given, or an option-shaped argument

# KNOWN ALIASES

    kiosk -> kiosk.lab.tcos.us
