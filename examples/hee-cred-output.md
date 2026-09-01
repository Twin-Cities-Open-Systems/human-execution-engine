# `hee-cred` — real run

Real trigger: "we need to get you all the keys, need a key store...
key/pass store now." Three real scoping decisions from Spencer before
any code was written (not assumed): git-tracked ciphertext storage,
exec-only retrieval (never printed), and multiple accounts from the
start.

Dogfooded against an isolated, throwaway GPG keyring generated purely
for this test (`hee-cred-test@example.invalid`, 1-day expiry) — not any
real production key.

```
$ echo -n "s3kr1t-test-value-42" | gpg --encrypt --armor \
    -r hee-cred-test@example.invalid -o .hee/secrets/spencer@kiosk.gpg
```

(That's the equivalent of what `hee-cred -seal spencer@kiosk -recipients
hee-cred-test@example.invalid` does interactively — `-seal` itself
couldn't be dogfooded in this sandbox since it deliberately refuses to
run without a real TTY, which is exactly the safety property being
tested, not a gap.)

Retrieval, verified **without ever printing the plaintext** — the
consuming command hashes it and only the hash is compared:

```
$ hee-cred -pass spencer@kiosk -exec bash -c \
    'echo -n "$HEE_CRED_PASS" | sha256sum | cut -d" " -f1'
3130fe4a82fd07f20a7f02b4e4021c2ac46206eb70dc7602b55a68aba3f97cd8

$ echo -n "s3kr1t-test-value-42" | sha256sum | cut -d" " -f1
3130fe4a82fd07f20a7f02b4e4021c2ac46206eb70dc7602b55a68aba3f97cd8
```

Hashes match — round trip is correct, and at no point does the real
value appear in this tool's own output.

Re-verified 2026-08-29 against current `main`: `-pass -exec` no longer
prints a `hee-cred: decrypted '<account>', running: [...]` diagnostic
line before this — real trigger, that line leaked into an irssi
channel via `hee-scrob`'s own `-exec` wiring
(https://github.com/Twin-Cities-Open-Systems/human-execution-engine/pull/431).
Output above reflects current behavior, not the removed line.

## Real safety checks, all verified

```
$ echo "fake-piped-secret" | hee-cred -seal test@host -recipients x@y
hee-cred: -seal requires an interactive terminal -- refusing to read a secret from a pipe/redirect/script

$ hee-cred -pass nonexistent@host -exec echo hi
hee-cred: no sealed credential at .hee/secrets/nonexistent@host.gpg

$ hee-cred -pass spencer@kiosk
hee-cred: -exec <command...> required -- hee-cred never prints a decrypted secret directly
```

## Real extension: `-genfrom`, corpus-derived passphrases

Real trigger: "build cool wordlists... can be for play slip word
thingys." Real words pulled from real media dialogue (same rg-backed
search as `hee-srtscan`), CSPRNG-picked from the real matches, joined
into a SLIP-39/Diceware-shaped passphrase -- generated, not typed, so
it skips the interactive-terminal prompt, but stays unprinted the same
as the typed path.

```
$ hee-cred -seal southpark-demo -recipients hee-cred-test@example.invalid -genfrom "south park" -blocks 4
hee-cred: generated a 4-word passphrase from real dialogue matching 'south park' (not shown)
hee-cred: sealed -> .hee/secrets/southpark-demo.gpg (recipients: hee-cred-test@example.invalid)

$ hee-cred -pass southpark-demo -exec bash -c 'echo -n "$HEE_CRED_PASS" | sha256sum; echo -n "$HEE_CRED_PASS" | wc -c; echo -n "$HEE_CRED_PASS" | grep -oE "\-" | wc -l'
a8bc411a3c15c57f12adca6b13ece3c89b8c9b0306cfcf29037e9c5191f9aea1  -
20
3
```

4 real words, 3 dashes, correct shape -- verified via hash/length/dash-count only, the actual passphrase never printed.

Real footgun caught mid-build: `rg --json` uses a `bytes` (base64)
field instead of `text` for lines that aren't valid UTF-8 -- real
subtitle files hit this. Fixed to skip those lines rather than crash.

## Explicitly not built here

- No key-recovery/rotation flow -- if the recipient set changes, an
  existing sealed file needs re-sealing under the new recipients. Real
  gap, not hidden.
- No integration with `fleet-ops/bin/seal-secret.sh` yet -- that script
  covers multi-recipient sealing for one-off secrets; `hee-cred` is the
  account-keyed store. Worth reconciling into one tool later rather than
  carrying two, not done tonight.
- `ps`/`/proc` exposure: passing via env var (not argv) avoids `ps aux`
  visibility, but a root user or the same Unix user can still read
  `/proc/<pid>/environ` for the life of the child process. Real,
  unavoidable limit of any subprocess-env-based handoff on a shared
  host -- not a hee-cred-specific flaw, but worth knowing.
