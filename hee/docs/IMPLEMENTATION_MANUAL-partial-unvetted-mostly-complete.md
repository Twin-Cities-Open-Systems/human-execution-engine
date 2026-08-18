# HEE Core System Integrity & Low-Abstraction Governance Blueprint

This document defines the complete technical architecture for the HEE architecture, establishing a low-abstraction, high-sovereignty framework across the Fleet Org, Human Rights Org, and Machine Rights Org without relying on heavy enterprise cloud abstractions.

---

## 1. Shifting Integrity to the Kernel: How and Why fs-verity Exists

### Why It Exists
In traditional Linux file integrity monitoring systems, verifying that an operational asset or configuration file has not been altered requires reading the entire file into memory to compute a standalone SHA256 string. For continuous multi-agent environments, running a full cryptographic check every time an agent opens a contract, script, or MIB definition file introduces massive disk I/O overhead and performance bottlenecks.

The `fs-verity` facility resolves this by executing transparent, on-demand, block-level integrity verification directly inside the Linux kernel virtual filesystem (VFS) layer. Instead of hashing the entire file at once, the system constructs an immutable Merkle tree out of individual 4KB file blocks.

### Internal Mechanics
1. **Merkle Tree Construction:** The target file is passed to the kernel via an `ioctl` system call. The kernel breaks the file content into 4KB blocks, generates cryptographic hashes for each block (the leaves), and repeatedly pairs those hashes upward until it derives a single master string: the **fs-verity digest** (the Merkle root).
2. **Persistence and Immutability:** The filesystem appends and hides this Merkle tree metadata directly past the end of the file. The file is instantly marked with an immutable flag in the VFS layer. Once enabled, the file becomes strictly read-only; even the `root` user cannot alter, truncate, or append data to it. The file can only be deleted (unlinked).
3. **On-Demand Page Verification:** When an agent loop reads a specific section of a contract file, the filesystem driver intercepts the read operation. It only fetches and hashes the specific 4KB data blocks required, matching them up the cached Merkle tree branch to verify integrity against the root digest. If unauthorized block manipulation occurs directly on disk via malicious firmware or raw blocks injection, the kernel intercepts the page cache pull, detects the hash mismatch, blocks userspace access, and raises an `EIO` (Input/output error).

### Application to the HEE Tri-Branch Taxonomy
By applying `fs-verity` to your contract repositories (`/hee/contracts/`), your **Machine Rights Org** achieves kernel-enforced isolation:
* The `.yaml` files containing peer and senior authority rules are frozen in place.
* The file's unique `fs-verity digest` is compiled directly into your SNMP MIB tree as a static, unalterable identifier for that exact state of logic.
* Rogue or compromised agent scripts cannot bypass their stated boundaries because the execution environment cannot be modified on the fly.

---

## 2. Hardening Temporal Anchors Without Physical Rooftop Antennas

To validate permissions relative to your `hee-epoch` without deploying expensive Stratum-1 GPS time tracking antennas on every physical fleet chassis, implement a hybrid strategy using cryptographically secure time protocols coupled with logical watermarking.

### Step A: Network Time Security (NTS)
Standard Network Time Protocol (NTP) is inherently vulnerable to man-in-the-middle spoofing, allowing an attacker to inject artificial packet delays or shift a node's system clock into the past to make expired contracts appear valid. Instead of standard NTP, run an open-source, lightweight NTS client (such as `chrony`) pointed to public Network Time Security servers. NTS secures time synchronization using TLS to encrypt and authenticate time packets, ensuring that the time signals received over standard cellular or radio channels are accurate and un-tampered, without needing local GPS reference clocks.

### Step B: Cryptographic Monotonic Ratcheting
Since your MIB and contracts measure duration using sequential ticks elapsed since the `hee-epoch`, you can enforce time sequence rules mathematically:
* **The Local Watermark:** Every physical node maintains a strictly monotonic internal counter (`CLOCK_MONOTONIC`).
* **The Sequence Check:** Every incoming command, signed contract (`.yaml.asc`), or peer message must contain a timestamp value greater than or equal to the last recorded timestamp processed by that node.
* **The Result:** Even if a node's clock skews slightly due to crystal oscillator drift, it can never have its timeline forced backward by an attacker. Time within the fleet becomes a unidirectional cryptographic ratchet; commands from the past are instantly dead on arrival.

---

## 3. Exploiting the Internet Overlay: Low-Abstraction DNS and MTA

Instead of constructing heavy distributed consensus mechanisms, you can exploit standard DNS and SMTP servers to handle secure directory lookup and asynchronous messaging.

### DNS as an Immutable Key-Value Directory
DNS is a globally available, distributed, read-heavy caching database. By activating **DNSSEC** on your domain, you convert standard zone files into a cryptographically signed public ledger.

| Protocol / Record Type | HEE Operational Mapping | Operational Benefit |
| :--- | :--- | :--- |
| **TXT Records** | Map your `Machine Rights` identifiers directly to public GPG keys. For example, a lookup for `nuc1-claude._agents.yourdomain.org` returns its public key string or `fs-verity` root digest. | Eliminates the need for a dedicated key distribution server. Agents pull public keys via basic command-line `dig` or `nslookup`. |
| **TLSA / DANE Records** | Store fingerprints of TLS certificates for your machine-to-machine APIs directly inside the DNS zone file. | Agents don't need to trust broad commercial Certificate Authorities. If the local agent connects to a peer node, it checks the TLSA record via DNSSEC to confirm the connection is secure. |

### MTA (Mail Transfer Agents) as Asynchronous Command Pipelines
Using a standard, minimalist mail loop (like `postfix`) to pipe messages across the fleet provides built-in network tolerance that modern HTTP webhooks or MQTT message queues lack.

* **Store-and-Forward by Design:** If a mobile vehicle chassis enters a geographic dead zone with zero cellular connectivity, modern APIs throw unhandled timeout exceptions. A standard Mail Transfer Agent is explicitly engineered to handle disconnects; it safely queues the command email locally and retries delivery automatically for days until connectivity resumes.
* **Cryptographic Envelopes over SMTP:** Commands are sent across the mail pipeline as raw ASCII-armored PGP text. When the mail drops into the local agent node's local mailbox (`/var/mail/agent`), a shell script uses a basic Unix pipe to feed the message directly into `gpg --verify`. If the email is signed by a valid `senior-authority` fingerprint listed in the MIB, the script extracts the embedded YAML parameter and applies it immediately.

---

## 4. Public vs. Private Repository Architecture & Cryptographic Boundaries

By shifting your operational manifests to an entirely public taxonomy under `Twin-Cities-Open-Systems`, you enforce maximum transparency while protecting the core execution layers through strict GPG signing. The proprietary algorithmic core (`thesis-engine`) sits behind an absolute air-gapped on-premises perimeter, interacting with the public layers exclusively through local network interfaces.

### The Public Infrastructure Track
These repositories contain zero intellectual property or secrets. Security relies entirely on cryptographic integrity, not obscurity.

| Repository Name | Access | Purpose / Execution Layer | Key Contents & Manifests |
| :--- | :--- | :--- | :--- |
| `hee` | **Public** | Absolute root specification and cryptographic genesis point. | Core ASN.1 MIB source files, root OID allocation maps, universal `hee-epoch` baseline calculations, and the base image definitions for the NOTAI OS bare-metal underlay. |
| `fleet-ops` | **Public** | Main physical execution worker engine. | Telematics polling scripts, hardware-level chassis drivers, automated local `snmpset` configuration utilities, and raw device communication protocols. |
| `human-ops` | **Public** | Governance manifests for the Human Rights Org branch. | Explicit labor compliance constraints, public GPG keys for human keyservers, safety-driver threshold manifests, and human-override escalation workflows. |
| `machine-ops` | **Public** | Orchestration manifests for the Machine Rights Org branch. | Peer-to-peer and senior-authority contract templates (`.yaml`), agent validation runtimes, and local multi-agent consensus validation hooks. |
| `www-*` (e.g., `www-tcos`) | **Public** | Public-facing operational status web underlay. | Static dashboards reading anonymous public telemetry exported from your central SNMP monitors, rendering the current active state of the fleet transparently. |

### The Private Brain Track
This represents your financial engine. It is strictly isolated from public source control providers.

| Repository Name | Access | Purpose / Execution Layer | Cryptographic Isolation Mechanism |
| :--- | :--- | :--- | :--- |
| `thesis-engine` | **Private (On-Prem)** | The proprietary financial heuristic engine, alpha generation models, and high-frequency trading execution loops. | Hosted on local physical hardware. It pulls public data from `machine-ops` and `fleet-ops` to assess fleet state, but reads its own internal weights locally. It maps its final execution decisions down to simple binary outputs or specific OID writes to control the public fleet. |

---

## 5. Scaling High-Availability SNMP vs. Standard Cloud IaC

Traditional cloud-IaC (Kubernetes controllers, Terraform state engines) suffers from massive operational load because it relies on heavy user-space reconciliation loops. A typical Kubernetes agent consumes hundreds of megabytes of RAM just to continuously parse verbose JSON/YAML strings, fetch states from HTTP endpoints, and manage massive state databases.

### Operational Load Comparison
* **Standard Cloud IaC:** String-heavy, continuous JSON parsing, high memory footprint, platform lock-in, and synchronization lock latency.
* **HEE MIB-as-Source-of-Truth:** Integer-heavy primitive lookups, memory-mapped kernel VFS execution (`fs-verity`), near-zero CPU context switching, and a tiny memory footprint (<20MB per node for a full daemon).

### Engineering 132k Daemons via Stateless LVS
Trying to terminate 132,000 distinct nodes via a user-space proxy can create performance bottlenecks at scale. Because SNMP relies on stateless UDP packets over port 161, you can handle massive scale using a stateless architecture:


1. **IP Anycast Front-End:** Assign a single Virtual IP (VIP) to your core collection network using BGP Anycast routing. The internet naturally routes UDP packet traffic to the closest operational data center node, distributing the 132k node load globally.
2. **Keepalived / Linux Virtual Server (LVS):** Inside each data center, use `keepalived` to drive LVS at the kernel layer. LVS intercepts the incoming UDP datagrams and passes them directly to your backend pool of collector engines using Direct Server Return (DSR) or Layer 4 NAT.
3. **The Result:** The load balancer never extracts the packet payload to user-space; it shuffles UDP frames at the raw wire layer, achieving maximum throughput with minimal hardware overhead.

[ 132,000 Remote Nodes ] ──(UDP Port 161)──> [ IP Anycast Cluster ] ──> [ Keepalived / Kernel LVS ] ──> [ Net-SNMP Backends ]
