# Capacity Planning Methodology (pve buildout)

A repeatable process, not a one-off document -- this is "how we plan
capacity," worked out live during the first real pass
([fleet-ops#285](https://github.com/Twin-Cities-Open-Systems/fleet-ops/issues/285)),
generalized here so the next phase (and the next host, if one ever
exists) follows the same real steps instead of starting from scratch.

## The real steps

1. **Inventory before planning, always live-checked.** Never plan
   against assumed or remembered specs -- real CPU/RAM/disk/storage
   state, checked directly (`lscpu`, `free`, `pvesh get .../storage`,
   `df`), every time. Caught twice already in #285's own history:
   `nuc-1` was assumed to be Proxmox and wasn't; the pve storage pools'
   real content-type support (`vmdata`/`local-lvm` already handle
   `rootdir`) unblocked LXC deployment ahead of the ZFS-root work
   nobody had checked was still outstanding.

2. **Map roadmap needs to real capacity, don't build ahead of a named
   need.** Every planned service traces to a real, linked reason
   (fleet-ops#155's roadmap, a real dogfood cohort, etc.) -- capacity
   sized for what's actually coming, not speculative headroom.

3. **Decompose into minimal deployable units.** One tiny, bare-minimum
   LXC per core service (bastion, MTA, snmpd, etc.), not a fat
   multi-service container -- matches this org's own documented
   djb/minimalism preference, applied at the container-topology level.
   A service that can't be scoped this small is a signal to decompose
   it further, not an exception to the rule.

4. **The host itself gets nothing new, ever.** `pve` (or any future
   hypervisor host) stays exactly as its base install leaves it -- no
   packages, no services, on the bare host. Everything real runs
   inside a container/VM. A capability check against the host's
   package repo (e.g. confirming `snmpd` exists in Debian's apt) is
   not the same as installing it there -- keep that distinction
   explicit in writeups so it isn't misread later.

5. **Deploy via a real, extensible API tool -- never manual/GUI
   clicks.** One declarative manifest per service (hostname, template,
   CPU/RAM/disk, network, storage target), fed to a tool that calls
   the real Proxmox API (`pvesh`/REST) to create and start it. Adding
   a new service is a new manifest entry, not new deploy code --
   that's what "extensible" means here, not a one-off script per
   container. (Real tool implementation tracked separately, pending
   coordination with whichever session already has one in flight --
   don't duplicate.)

6. **Track real allocation state as a manifest, not tribal knowledge.**
   Which service lives in which container, on which storage, sized
   how -- written down where the next planning pass (human or agent)
   can read it directly instead of re-discovering the whole host from
   scratch. The inventory step above should get cheaper every time
   this exists, not repeat full recon forever.

7. **Re-audit on a real trigger**, not an arbitrary calendar. Before
   any new roadmap phase, before any host's storage crosses a real
   threshold (see fleet-ops#284's own percentage-vs-absolute lesson --
   pick a real, absolute-headroom-aware trigger, not a bare
   percentage), or when a service's actual usage diverges from its
   planned footprint.

## Worked example so far

Steps 1-4 above are the real, lived history of fleet-ops#285/#287 and
[HEE#355](https://github.com/Twin-Cities-Open-Systems/human-execution-engine/issues/355)
tonight -- inventory caught two real wrong assumptions, roadmap mapping
picked the bastion/qmail/snmpd trio as the first real services, and
the host-purity rule got corrected live mid-plan. Steps 5-7 are the
next real work, not yet done.
