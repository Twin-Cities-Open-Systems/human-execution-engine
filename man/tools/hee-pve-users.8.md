% HEE-PVE-USERS(8) | HEE Tools

# NAME

hee-pve-users - hee-pve-users command

# SYNOPSIS

    hee-pve-users [-h] [--host HOST] [--dry-run] manifest

# DESCRIPTION

    positional arguments:
      manifest

    options:
      -h, --help   show this help message and exit
      --host HOST
      --dry-run


# EXAMPLES

    hee pve-users pve/users/roster.yaml --dry-run

    Not marked "# ci": even --dry-run reads the live Proxmox host's users to diff
    against the manifest, which a runner cannot reach.
