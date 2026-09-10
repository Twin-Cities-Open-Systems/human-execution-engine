% HEE-PVE-DEPLOY(8) | HEE Tools

# NAME

hee-pve-deploy - deploy and provision a Proxmox LXC from one declarative manifest

# SYNOPSIS

    hee-pve-deploy [-h] [--node NODE] [--host HOST] [--dry-run]
      hee-pve-deploy MANIFEST.yaml [--node pve] [--host 10.0.0.153] [--dry-run]
                     [--anchors FILE] [--addons FILE] [--agent-roster FILE]

    positional arguments:
      manifest              pve/services/<name>.yaml -- see the manifest format
                            above

    options:
      -h, --help            show this help message and exit
      --node NODE
      --host HOST
      --dry-run             resolve the manifest and print every command that
                            would run -- create, add-ons, files, provision --
                            creating and changing nothing. Without it the deploy
                            is applied.
      --anchors ANCHORS     registry of roles whose address may be pinned. A
                            manifest that declares address or hwaddr must name a
                            role listed there; anything else has its address
                            allocated.
      --addons ADDONS       the org's container-addons registry, the only place an
                            'addons:' name resolves. Unreadable means every add-on
                            is refused, never silently skipped.
      --agent-roster AGENT_ROSTER
                            the org's signed agent roster, the only place a model
                            is named. Read only by 'generate: agent-roster-model'
                            files entries; it must be ratified and its .asc must
                            verify, or nothing is rendered.

# DESCRIPTION

                          [--anchors ANCHORS] [--addons ADDONS]
                          [--agent-roster AGENT_ROSTER]
                          manifest

    hee-pve-deploy -- deploy and provision a Proxmox LXC from one declarative manifest.

    One YAML file per service; this tool creates the container via the real
    Proxmox API (pvesh over SSH to the node), idempotent by hostname, then
    applies the manifest's add-ons, files and provision scripts inside it.

    Real trigger (2026-08-24, Spencer): "build extensible deploy via api to
    pve strat" -- tiny, bare-minimum LXC per core service (bastion, qmail
    MTA, snmpd), matching docs/guides/PVE_CAPACITY_PLANNING_METHODOLOGY.md's
    step 5 ("a new service is a new manifest entry, not new deploy code").

    Never installs anything on the pve host itself -- pvesh is Proxmox's
    own real API-wrapper CLI, already there on any real Proxmox node; this
    tool just calls it over SSH from wherever hee runs.

    Manifest format (pve/services/<name>.yaml):
      hostname: bastion
      template: alpine-3.23-default_20260116_amd64.tar.xz
      cores: 1
      memory_mb: 256
      disk_gb: 4
      storage: ssd1
      bridge: vmbr0
      unprivileged: true
      addons: [agent-tooling]           # named apk sets from the org's registry (--addons)
      agent: ci-triage                  # agent roster role, only for a container that runs an agent
      files:                            # committed files pushed INTO the container
        - {src: pve/lab-dhcp/dnsmasq.conf, dst: /etc/dnsmasq.conf, mode: "0644"}
        - {generate: agent-roster-model, dst: /etc/claude-code/managed-settings.d/50-model.json, mode: "0644"}
      provision:                        # committed POSIX sh scripts run inside it
        - pve/lab-dhcp/provision.sh

    `files:` and `provision:` paths are relative to the root of the repo the
    manifest lives in (git rev-parse --show-toplevel), never to the current
    directory and never absolute: a manifest names what it ships, and what it
    ships is under review beside it. Real trigger (2026-09-10): the only
    precedent for configuring what runs INSIDE a container was a README of
    `pct exec N -- sh -c "cat > /etc/..."` one-liners (fleet-ops
    pve/snmp-joe/README.md) -- the same imperative shape pve/network.yaml was
    written to remove for bridges. Order: create -> addons -> files ->
    provision. The manifest is fully resolved BEFORE the container is created,
    so a missing file fails closed rather than leaving a half-provisioned
    container behind. Every step is previewed under --dry-run, including
    addons, which the dry run used to skip.

    A `files:` entry names either `src` (a committed file) or `generate` (a
    file rendered at deploy time, never committed). The one generator today is
    `agent-roster-model`: it reads the org's agent roster (--agent-roster), refuses unless
    the agent roster is `status: ratified` AND its detached signature verifies with a
    key the agent roster's own ratification_evidence names, then renders the
    Claude Code managed-settings drop-in that pins the manifest's `agent:` to
    the model the agent roster assigns. Real trigger (2026-09-10): the first agent
    manifests shipped five hand-kept managed-settings.json copies, each
    restating a model the signed agent roster already names -- a second source that
    would leave every container on the old model after an agent roster change, with
    nothing to say so. Operator: "generate from roster at deploy is correct,
    footgun". The model is named in exactly one place, and the dry run prints
    the rendered file.
