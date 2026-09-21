# The three IETF base modules, and why they are in this repo

`HEE-MIB.txt` and TCOS-MIB (fleet-ops) both `IMPORTS ... FROM` modules this org
did not write:

| Module | Defines what we import | RFC |
|---|---|---|
| `SNMPv2-SMI` | `MODULE-IDENTITY`, `OBJECT-TYPE`, `OBJECT-IDENTITY`, `Integer32`, `Counter64`, `enterprises` | 2578 |
| `SNMPv2-TC` | `TEXTUAL-CONVENTION`, `DisplayString`, `TruthValue` | 2579 |
| `SNMPv2-CONF` | `MODULE-COMPLIANCE`, `OBJECT-GROUP` | 2580 |

Without them net-snmp cannot parse either module at all -- not "with warnings",
not "partially". It reports `Cannot find module (SNMPv2-SMI)`, then
`Undefined identifier: enterprises`, then `Unknown Object Identifier` for every
name in both arcs. A walk still works, because the agent speaks numbers; what
breaks is every tool that turns a number into a name, which is `snmptranslate`,
`snmptable`, and any human reading output.

## Why they are here and not in fleet-ops as well

**TCOS-MIB cannot parse without HEE-MIB**: it imports `HeeStatus` from it. So a
run that sees only fleet-ops' `mib/` was already impossible, and `mib/walk`
there has required both directories on `MIBDIRS` since 2026-09-08. One copy in
this repo therefore serves both, and a second copy in fleet-ops would be two
files that can drift with nothing to notice.

Measured 2026-09-21, base modules present ONLY here:

```
$ MIBDIRS=~/git/fleet-ops/mib:~/git/human-execution-engine/mib MIBS=TCOS-MIB \
    snmptranslate -On TCOS-MIB::fleetState
.1.3.6.1.4.1.66550.1.1.1.6
```

## Why vendored rather than installed

Debian's `libsnmp-base` ships 13 MIBs and **none of these three**; the standard
set lives in `snmp-mibs-downloader`, which is non-free and downloads at install
time. Alpine's `net-snmp-mibs` ships 65 including all three, which is why ct113
can parse our modules and flippy could not.

Vendoring three small stable files beats making every host that wants to read
its own fleet's MIB either add a non-free repo or be an Alpine box. This is not
the vendoring rule 16 prohibits -- that is about copying **org tooling** between
repos, where three divergent `security_scanner.py` was the measured cost. These
are frozen IETF documents that have not changed since 1999.

## Provenance

Copied 2026-09-21 from ct113 (`tcos-snmp-joe`), `/usr/share/snmp/mibs/`, as
shipped by Alpine 3.23's `net-snmp-mibs` package -- so no download, and no
third-party fetch to pin. Recorded here because §15 asks for provenance and a
checksum on anything we did not write.

```
ece2355fc8b6140af702f86d77bd3f7398d80375fc6278c3e30ff3a31b53e0b7  SNMPv2-SMI.txt
c1379575e6a0ad25b2d7da68294153c1fd79750827376f2aa6323d072d73f0b8  SNMPv2-TC.txt
b3e90ba682e10c76f6de90e65a0013143f0ec531b0ed546b2b8aa5ad5c0001eb  SNMPv2-CONF.txt
```

Verify with `sha256sum -c` against the block above, or re-derive from any
net-snmp install.

## Using them

```sh
export MIBDIRS=$HOME/git/human-execution-engine/mib:$HOME/git/fleet-ops/mib
export MIBS=TCOS-MIB          # NOT +TCOS-MIB
```

`MIBDIRS` **replaces** net-snmp's search path rather than extending it, so the
system directory is left out on purpose -- there is nothing in it we need.

`MIBS=TCOS-MIB` loads that module and its imports only. `MIBS=+TCOS-MIB` means
"the default set as well", and the default set names two dozen standard modules
we do not carry, so every command prints two dozen `Cannot find module` lines
before doing its job.
