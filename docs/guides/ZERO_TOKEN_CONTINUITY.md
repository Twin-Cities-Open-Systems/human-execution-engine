# HEE Tool Cheat Sheet

Every `hee-*` tool in this repo, what it is for, and its man page.

**Zero-token by default.** Everything listed here is a plain local command:
no LLM call, no agent, nothing that costs tokens. Default to the
deterministic path -- but do not skip real, necessary work just to avoid
spending tokens. The principle is *cheapest tool that actually does the
job*, not *cheapest tool*.

**Invocation.** `hee-<tool>` on disk is `hee <tool>` on the command line;
both work. `hee list` prints the live inventory, including repo-local
extensions contributed by other repos.

**Help.** Every tool takes `help`, `--help` or `-h`. Help is for the verb to
its left, and nothing to the right of it is executed -- `hee check refs help
--fix` prints help and does not run `--fix`.

## Legend

| Mark | Meaning |
|---|---|
| [`hee tool`](https://man.tcos.us/) | Links to the published man page |
| ⁿ | No man page published yet |
| ˢ | Man page published but currently stale -- see below |

## 🔀 Git and PR flow

Branch, review, merge, and keep every checkout current.

| Command | What it does |
|---|---|
| [`hee git-merge`](https://man.tcos.us/gopher/0/hee-git-merge.txt) ˢ | Mass review/approve/merge open PRs, with dependency-aware batching |
| `hee worktree` ⁿ | Per-session git worktree, no extra clone |
| [`hee repo-refresh`](https://man.tcos.us/gopher/0/hee-repo-refresh.txt) ˢ | Per-repo health check and fast-forward pull worker |
| [`hee hooks-install`](https://man.tcos.us/gopher/0/hee-hooks-install.txt) ˢ | Install the optional git hooks, non-destructive and idempotent |
| [`hee vendor`](https://man.tcos.us/gopher/0/hee-vendor.txt) ˢ | Vendor HEE tooling into another repo |
| [`hee attach`](https://man.tcos.us/gopher/0/hee-attach.txt) ˢ | Attach a repo to the HEE toolchain |
| `hee lg` ⁿ | Compact git log view |
| `hee hg` ⁿ | Git helper shorthands |

## 🔎 Checks and lint

Catch org-specific rot that no external linter knows about.

| Command | What it does |
|---|---|
| [`hee check`](https://man.tcos.us/gopher/0/hee-check.txt) ˢ | Repo boundary, file-reference, regex, systemd and CLI-help checks |
| [`hee lint`](https://man.tcos.us/gopher/0/hee-lint.txt) ˢ | Lint gate for HEE-object YAML (apiVersion: hee/v1) |
| [`hee check-og`](https://man.tcos.us/gopher/0/hee-check-og.txt) ˢ | Open Graph / Twitter Card / title / canonical checks for a page |
| `hee check-cursor-prompts` ⁿ | Ensure .cursor/prompts matches the active HEE policy source |
| [`hee scan`](https://man.tcos.us/gopher/0/hee-scan.txt) | Named-target regex scan via ripgrep |
| `hee filter` ⁿ | Filter a stream against named patterns |
| [`hee srtscan`](https://man.tcos.us/gopher/0/hee-srtscan.txt) ˢ | Scan subtitle files |

## 🗂️ Objects, tickets and records

HEE's typed objects, and work tracked without a GitHub round-trip.

| Command | What it does |
|---|---|
| `hee ticket` ⁿ | Local ticket queue -- log work with no GitHub call at all |
| [`hee board`](https://man.tcos.us/gopher/0/hee-board.txt) ˢ | Board view over tracked work |
| `hee index` ⁿ | Persisted index of every HEE object |
| `hee contract-review` ⁿ | Smart-sorted contract review, needed-first |
| [`hee fields`](https://man.tcos.us/gopher/0/hee-fields.txt) ˢ | Set real issue fields (type, priority, effort) on a GitHub issue |
| [`hee inv`](https://man.tcos.us/gopher/0/hee-inv.txt) ˢ | Inventory tool |
| [`hee inv-receipt`](https://man.tcos.us/gopher/0/hee-inv-receipt.txt) ˢ | Receipt ingest for inventory |
| [`hee qdb`](https://man.tcos.us/gopher/0/hee-qdb.txt) | Quote search across a source document |
| [`hee name`](https://man.tcos.us/gopher/0/hee-name.txt) ˢ | Name allocation from managed pools |

## 🖥️ Hosts and infrastructure

Reach and inspect real TCOS hosts.

| Command | What it does |
|---|---|
| [`hee shell`](https://man.tcos.us/gopher/0/hee-shell.txt) ˢ | SSH into a known TCOS host by short alias |
| [`hee view`](https://man.tcos.us/gopher/0/hee-view.txt) ˢ | Check the sitemap against real hosts |
| [`hee net`](https://man.tcos.us/gopher/0/hee-net.txt) | Protocol-aware fetch: gopher, finger |
| [`hee pve-deploy`](https://man.tcos.us/gopher/0/hee-pve-deploy.txt) ˢ | Deploy a Proxmox manifest |
| [`hee pve-health`](https://man.tcos.us/gopher/0/hee-pve-health.txt) ˢ | Proxmox cluster health status |
| [`hee pve-users`](https://man.tcos.us/gopher/0/hee-pve-users.txt) ˢ | Manage Proxmox users from a manifest |
| [`hee ssh-send-keys`](https://man.tcos.us/gopher/0/hee-ssh-send-keys.txt) ˢ | Distribute SSH keys to hosts |
| `hee ssh-trust-ca` ⁿ | Trust an SSH certificate authority |
| [`hee quota`](https://man.tcos.us/gopher/0/hee-quota.txt) ˢ | Remaining/limit/reset per rate-limit pool |
| `hee stat` ⁿ | Host and service status |

## 🔐 Secrets and identity

GPG-backed, local, no service dependency.

| Command | What it does |
|---|---|
| [`hee cred`](https://man.tcos.us/gopher/0/hee-cred.txt) | Minimal GPG-backed credential store: seal, and exec with a secret |
| [`hee pwgen`](https://man.tcos.us/gopher/0/hee-pwgen.txt) | Cryptographically secure password generator |
| [`hee qr`](https://man.tcos.us/gopher/0/hee-qr.txt) | Reader for an mt-logo-render hee-key hole anchor |

## 📤 Publish and output

Turn local state into something readable elsewhere.

| Command | What it does |
|---|---|
| `hee publish` ⁿ | Activity/status report pulled straight from the GitHub Events API |
| `hee site-publish` ⁿ | Publish files to the Cloudflare Pages project |
| [`hee gen-manpages`](https://man.tcos.us/gopher/0/hee-gen-manpages.txt) ˢ | Man-page generator -- derives pages from each tool's own help |
| [`hee print`](https://man.tcos.us/gopher/0/hee-print.txt) ˢ | Pretty-print JSON/YAML/Markdown/Text using jq/yq when available |
| [`hee url`](https://man.tcos.us/gopher/0/hee-url.txt) ˢ | URL shortener and tagger |
| [`hee exif`](https://man.tcos.us/gopher/0/hee-exif.txt) ˢ | Read image EXIF metadata |
| [`hee scrob`](https://man.tcos.us/gopher/0/hee-scrob.txt) | Terse now-playing scrobble |
| [`hee con`](https://man.tcos.us/gopher/0/hee-con.txt) ˢ | Connect to IRC with a native client, persistent in tmux |
| [`hee sqz`](https://man.tcos.us/gopher/0/hee-sqz.txt) ˢ | Squeeze a loop's OK:/FAIL: lines into one pass-ratio JSON line |

## 🧰 Toolchain upkeep

Keep the tools themselves honest.

| Command | What it does |
|---|---|
| `hee ver` ⁿ | Version and verification discovery -- versions, platform, hardware, session |
| `hee tools` ⁿ | Router for the external-toolchain check/update pair |
| `hee tools-check` ⁿ | Presence and version of every external tool in the manifest |
| `hee tools-update` ⁿ | Install/refresh the external tools the manifest names |
| [`hee reset-tooling`](https://man.tcos.us/gopher/0/hee-reset-tooling.txt) ˢ | Conservative reset-to-new for stray tool state |
| [`hee cache-prune`](https://man.tcos.us/gopher/0/hee-cache-prune.txt) ˢ | Prune stale entries from the hee disk cache |
| `hee sync-cursor-prompts` ⁿ | Sync canonical HEE prompts into the Cursor location |
| [`hee procmail`](https://man.tcos.us/gopher/0/hee-procmail.txt) ˢ | Mail filtering helper |

## Status vocabulary

Every tool reports in one vocabulary -- the Nagios plugin API, adopted
rather than invented. Machine consumers parse the **label**, never the icon.

| Icon | Label | Exit | Meaning |
|---|---|---|---|
| ✅ | `OK` | 0 | Nothing to act on |
| ⚠️ | `WARNING` | 1 | Degraded, still functioning |
| ❌ | `CRITICAL` | 2 | Broken, needs action |
| ❓ | `UNKNOWN` | 3 | Could not determine |

Status always ships as icon **and** text label, never color alone, and the
icons are shape-distinct rather than hue-only. Set `HEE_STATUS_STYLE` to
`icon` (default), `ascii` or `plain` in your `heerc`; preview with
`hee_status_demo`.

## Man page freshness

Measured 2026-08-31 against the live site, by fetching each page and
reading its content:

| Status | Count | Detail |
|---|---|---|
| ✅ `OK` | 7 | Real man page content |
| ⚠️ `WARNING` | 30 | Published, but showing captured tool output (`ˢ`) |
| ❌ `CRITICAL` | 17 | No page published at all (`ⁿ`) |

The 30 stale pages are a downstream effect of tools whose help did not work:
`hee-gen-manpages` derives each page from the tool's own help output, so a
tool that runs instead of printing help gets its *run output* published as
documentation. The published `hee-check` page, for example, contains
`find: unknown predicate '--help/prompts'` rather than a synopsis.

Do not judge a page by its HTTP status: the gopher-to-HTML gateway returns
**200 for pages that do not exist**, with `Error: File or directory not
found!` in the body. Check the body, not the code.

The end-to-end flow from editing a tool to a page appearing on man.tcos.us
is documented in `docs/guides/MANPAGE_PIPELINE.md` -- including the stage that
is still manual.

## Needs real judgment -- queue it, do not force it

These are not zero-token work. Log them with `hee ticket` so they are ready
when a session is available:

- Novel bug diagnosis on something not already understood
- Doctrine or policy writing that needs synthesis, not a template fill
- Review judgment beyond "does CI pass" (a human `y/N` in `hee git-merge`
  is fine; writing new review comments that reason about a diff is not)
- Anything needing cross-referencing across repos to reach a decision

## Coming back after a gap

A returning session's first moves: a `git fetch`/pull sweep across the repos
touched during the gap (`hee repo-refresh`), then `hee ticket` to read the
local queue. That queue is the real record of what happened while nothing
was running -- chat scrollback is not.
