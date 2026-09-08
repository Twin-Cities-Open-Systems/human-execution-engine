% HEE-PVE-HEALTH(1) | HEE Tools

# NAME

hee-pve-health - hee-pve-health command

# SYNOPSIS

    hee-pve-health [-h] {status,inventory,map,drift,warn} ...

# DESCRIPTION

    positional arguments:
      {status,inventory,map,drift,warn}
        status              node, storage overcommit and per-container state
        inventory           the container table, rendered from the pve API
        map                 topology as mermaid; --term for a terminal, --proposed
                            for the roster, --diff for the build queue
        drift               do the committed artifacts still match the machine?
        warn                exit 1 on real overcommit or a container that is not
                            running

    options:
      -h, --help            show this help message and exit
