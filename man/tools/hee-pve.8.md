% HEE-PVE(8) | HEE Tools

# NAME

hee-pve - the pve family, and the host network read from a yaml.

# SYNOPSIS

    hee-pve [-h] {network,deploy,health,users,dispatch} ...

# DESCRIPTION


    Real trigger (2026-09-09): Spencer, after being handed a five-mutation shell
    one-liner to paste at his own hypervisor -- "that is madness ... should be a
    pve tool and use yml's to configure the network. hee pve -things and stuff."

    He was right twice. The one-liner was unreviewable, and it existed only
    because the host's network was the ONE layer of this fleet with no object.
    `pve/services/*.yaml` declares containers and `hee pve deploy` applies them;
    `network-anchors.registry.v1.yaml` declares which roles may pin an address at
    all. But all fourteen manifests say `bridge: vmbr0` and NOTHING declared that
    vmbr0 exists. A thing with no object gets configured imperatively, every
    time, by whoever is standing closest.

    So: `pve/network.yaml` declares the host's bridges, and this reconciles.

      hee pve network              dry run -- report declared vs measured
      hee pve network --apply      apply the difference (additive only)
      hee pve deploy|health|users|dispatch  the existing tools, unchanged

    DRY RUN IS THE DEFAULT, the same contract hee-gen-manpages and hee-release
    already keep. A tool that mutates a hypervisor on a bare invocation is how an
    operator loses a network, and this one edits /etc/network/interfaces.

    WHAT IT WILL NOT DO, by construction rather than by intention:
      - delete a bridge. It creates and it sets sysctls. Removal is an operator
        action with a rollback file in hand.
      - touch vmbr0. The household side is not this file's business, and an
        additive tool that can still break the box it runs on is not additive.
      - write a container address. The anchors registry is explicit that a role
        is pinned by a DHCP reservation on its MAC, never by writing an IP. A
        BRIDGE is not a role -- it is the hardware addresses are handed out on.

    FAILS CLOSED. A host that cannot be read is UNKNOWN (exit 3), never "no
    changes needed". `namespace-audit` reported OK across 17 repos every day for
    a week while its token was empty and it had read none of them; a green from a
    control that is not looking is worse than a red.

    BEFORE IT WRITES, it checks that /etc/network/interfaces already loads
    (`ifreload -a -n`). A file that does not parse is a refusal (exit 3) naming
    the offending lines, not a half-finished apply -- pve's file had been
    malformed since 2026-02-15 and this tool appended to it correctly, then died
    on somebody else's seven-month-old lines with a stanza already written.

    ON FAILURE IT ACTUALLY ROLLS BACK. An ERR trap restores the backup and
    reloads. Until 2026-09-09 the tool printed "rollback: <path>", restored
    nothing, and left its own partial write live on the hypervisor; the
    announcement was what stopped anyone checking. The backup line now says
    "backup:", because that is all it is until something fails. The restore
    covers /etc/network/interfaces ONLY -- a sysctl persist file and a `pveum
    acl modify` are additive and separately reversible, and this is not a
    transaction.

    Exit codes are the Nagios convention this org already uses everywhere:
    0 OK, 1 WARNING (drift), 2 CRITICAL, 3 UNKNOWN.

    positional arguments:
      {network,deploy,health,users,dispatch}
        network             reconcile the host's bridges against pve/network.yaml
        deploy              passthrough to hee-pve-deploy
        health              passthrough to hee-pve-health
        users               passthrough to hee-pve-users
        dispatch            passthrough to hee-pve-dispatch

    options:
      -h, --help            show this help message and exit
