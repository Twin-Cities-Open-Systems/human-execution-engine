# HEE Hardware Discovery Spec

```yaml
schema:
  name: HEE-Hardware-Discovery
  version: 0.1.0
  strict: true
  status: draft
meta:
  iter: 15
  intent: "Nagios-style discovery down through sysfs/devfs, with board-level telemetry where available."
  principles:
    - evidence_over_assertion
    - disk_first_artifacts
    - read_only_by_default
    - least_privilege
    - correctness_over_completion
  gnu_name:
    priority: p0
    note: "Seed candidates now; final GNU name selection required before tagging."
    candidates:
      - gnu-pill
      - gnu-free
```

## 0. Scope

This spec defines a **read-only, evidence-producing** hardware/host discovery system (“hee-discover-hw”) that:

- inventories **listeners** (TCP/UDP + Unix sockets)
- inventories **hardware surfaces** under `/sys` and `/dev`
- captures **host basics** (cpu/mem/disk/load)
- detects **consumables** (Prometheus-ish endpoints, Nagios-ish ports, files, sockets)
- emits **durable artifacts** suitable for governance, CI, and operator debugging

Non-goals:

- imaging PCB traces or physical inspection
- writing to hardware buses by default (I²C/SPI/GPIO writes are hazardous and out-of-baseline)

## 0.1 Docs Review Requirement (Release Gate)

Any change that lands this spec or its implementation MUST ensure:

- docs are reviewed for accuracy (no stale claims, no implied capabilities)
- docs are updated where needed (ops index, status docs, release notes templates if touched)

Minimum evidence:

- the discovery artifacts exist on disk (history/…)
- the relevant docs links resolve (no broken references introduced)

## 1. Terms

- **Surface**: A kernel-exposed interface (sysfs path, dev node, socket, port, file).
- **Consumable**: A surface intended to be consumed by tooling (metrics endpoint, exporter port, status file, socket).
- **Evidence artifact**: On-disk JSON/MD output generated from live discovery, timestamped, immutable in history.
- **Privilege level**:
  - L0: unprivileged (default)
  - L1: elevated read (sudo for read-only where required)
  - L2: hazardous (bus writes / debugfs toggles) — **not baseline**

## 2. Outputs (Disk Evidence)

All runs produce a unique stamp directory:

- `docs/history/ops/discovery/<UTCSTAMP>/`
  - `MANIFEST.json` (what ran, versions, environment summary, privilege level)
  - `LISTENERS.json` + `LISTENERS.md`
  - `HOST.json` + `HOST.md`
  - `SURFACES.json` + `SURFACES.md`
  - `CONSUMABLES.json` + `CONSUMABLES.md`
  - optional: `DEEP.json` + `DEEP.md` (tracefs/debugfs/perf summaries) gated by privilege

Artifact invariants:

- deterministic ordering of lists
- explicit “not available” reasons (permission, missing feature, platform mismatch)
- never claim ownership attribution if not proven (PID mapping best-effort)

## 3. Tooling Constraints (Operator-Friendly)

Baseline must work with:

- Python 3 stdlib
- core unix tools available on most distros (e.g., `ss`, `lsof` optional)
- “unix fuckery” allowed, but **scripted** and evidence-producing

Policy constraints:

- no shell-script blobs embedded in YAML
- read-only baseline must not mutate system state

## 4. Discovery Ladder (15 Iterations)

This is the canonical 15-step probe plan. Each step MUST either:

- produce evidence, or
- produce an explicit `unavailable` record with a reason.

### iter 1 — Environment + platform identity (L0)

Collect:

- hostname, kernel version, distro (best effort), arch
- python version, uid/euid, container hint (best effort)
Evidence:
- `MANIFEST.json`

### iter 2 — Process/network listeners (TCP/UDP) (L0/L1)

Collect:

- listening TCP sockets (v4/v6)
- bound UDP sockets (v4/v6)
- best-effort PID/comm mapping via `/proc/*/fd`
Evidence:
- `LISTENERS.json` + `LISTENERS.md`

### iter 3 — Unix domain sockets (L0/L1)

Collect:

- `/proc/net/unix` enumeration
- best-effort PID mapping
Evidence:
- `LISTENERS.json` (unix entries) + `LISTENERS.md` section

### iter 4 — Host basics: CPU/mem/load (L0)  [gnu-name seed: gnu-pill]

Collect (Linux):

- `/proc/loadavg`
- `/proc/meminfo` (MemTotal/MemAvailable)
- cpu count + model (best effort)
Evidence:
- `HOST.json` + `HOST.md`

### iter 5 — Host basics: disk + mounts (L0)

Collect:

- `shutil.disk_usage("/")`
- `/proc/mounts` inventory (bounded)
Evidence:
- `HOST.json` + `HOST.md`

### iter 6 — sysfs topology roots (L0)

Collect presence + bounded inventory for:

- `/sys/devices`
- `/sys/bus`
- `/sys/class`
- `/sys/firmware` (if present)
Evidence:
- `SURFACES.json` + `SURFACES.md`

### iter 7 — /dev capability map (L0)

Collect (bounded):

- enumerate `/dev` nodes and highlight known high-signal nodes:
  - i2c: `/dev/i2c-*`
  - spi: `/dev/spidev*`
  - gpio: `/dev/gpiochip*`
  - tpm: `/dev/tpm*`
  - drm: `/dev/dri/*`
  - nvme: `/dev/nvme*`
  - block: `/dev/sd*`, `/dev/dm-*`, `/dev/md*`
Evidence:
- `SURFACES.json` + `SURFACES.md`

### iter 8 — hwmon sensors (temps/volts/fans/power) (L0/L1)

Collect:

- `/sys/class/hwmon/hwmon*/` keys:
  - `name`, `*_label`, `temp*_input`, `in*_input`, `fan*_input`, `power*_input`, `curr*_input`
Evidence:
- `SURFACES.json` + `SURFACES.md` (hwmon section)

### iter 9 — thermal zones + cooling devices (L0/L1)  [gnu-name seed: gnu-free]

Collect:

- `/sys/class/thermal/thermal_zone*/` (type, temp, trips if accessible)
Evidence:
- `SURFACES.json` + `SURFACES.md` (thermal section)

### iter 10 — powercap / energy counters (best effort) (L0/L1)

Collect:

- `/sys/class/powercap/` if present (Intel RAPL, etc.)
Evidence:
- `SURFACES.json` + `SURFACES.md` (powercap section)

### iter 11 — storage deep: NVMe/SATA health (best effort) (L0/L1 + optional tools)

Collect:

- sysfs inventory:
  - `/sys/class/nvme/`, `/sys/block/`
Optional (if tools present; still read-only):
- `nvme smart-log` (NVMe) or `smartctl -a` (SATA) — captured as raw text artifacts
Evidence:
- `SURFACES.json` + optional raw logs + summary in `SURFACES.md`

### iter 12 — network phys-ish signals (L0)

Collect:

- `/sys/class/net/*/`:
  - carrier, operstate, speed/duplex (if present), stats counters
Optional:
- if `ethtool` present, capture `ethtool <iface>` output (read-only)
Evidence:
- `SURFACES.json` + optional raw logs + summary

### iter 13 — error signals: EDAC/MCE/RAS (best effort) (L0/L1)

Collect:

- `/sys/devices/system/edac/` if present
- kernel log hints are out-of-scope unless explicitly captured as evidence via a tool
Evidence:
- `SURFACES.json` + `SURFACES.md` (ras section)

### iter 14 — PCIe link state + hints (best effort) (L0/L1)  [gnu-name seed: gnu-pill]

Collect:

- `/sys/bus/pci/devices/*/` bounded keys (if present):
  - `vendor`, `device`, `subsystem_*`
  - `current_link_speed`, `current_link_width` (if exposed)
Evidence:
- `SURFACES.json` + `SURFACES.md` (pcie section)

### iter 15 — consumables synthesis (L0)

Derive:

- “consumables” from listeners + known ports + HTTP probe of localhost (optional, bounded):
  - common Prometheus exporters (9100, 9115, 9187, etc.)
  - SNMP (161/udp), NRPE (5666), statsd (8125/udp)
- classify each consumable with:
  - kind: tcp/udp/http/unix/file/sysfs/dev
  - address/path
  - hint (if any)
  - evidence (e.g., http 200, skipped non-local, permission denied)
Evidence:
- `CONSUMABLES.json` + `CONSUMABLES.md`

## 5. Safety Guardrails

Baseline MUST:

- never write to:
  - `/dev/i2c-*`, `/dev/spidev*`, `/dev/gpiochip*`
  - sysfs attributes that mutate state
  - debugfs/tracefs controls
- treat “best effort” as:
  - enumerate paths + read-only values when permitted
  - otherwise record `unavailable_reason`

Hazard tiers:

- L0 safe (default)
- L1 elevated read (sudo read)
- L2 hazardous (bus writes / debug toggles) — requires explicit operator intent and separate RFC

## 6. Determinism Requirements

- stable sort order for emitted lists:
  - paths lexicographic
  - listener tuples `(proto, ip, port, path)`
- timestamps only in manifest + top-level metadata
- bounded outputs:
  - cap per section (e.g., first N files, first N sockets) with explicit truncation notes

## 7. Minimal CLI Contract (Implementation Target)

`hee-discover-hw` (or `scripts/hee-discover-hw.py`) MUST support: <!-- hee-check:refs-ok  an implementation target; this spec is what would build it -->

- `--out <dir>` (default: `docs/history/ops/discovery/<UTCSTAMP>`)
- `--level L0|L1` (default L0)
- `--format json|md|both` (default both)
- `--probe-http` (default off; only localhost binds; bounded paths)

## 8. CI Notes

- GitHub-hosted runners have limited access to real hardware surfaces; discovery MUST still be correct:
  - produce artifacts showing what is accessible
  - never pretend hardware exists
- Self-hosted runners enable full HWOps candy store (optional).

## 9. Next RFCs (Not Included Here)

- RFC: HEE I²C/SPI/GPIO Safety (read-only baseline; writes gated; hazard labeling)
- RFC: RAS/AER Signal Semantics (corrected errors as trend signals; escalation semantics)
- RFC: Deep Tracing Mode (tracefs/debugfs/perf) with explicit blast-radius guardrails
