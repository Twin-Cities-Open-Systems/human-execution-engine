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
hee-cred: decrypted 'spencer@kiosk', running: ['bash', '-c', '...'] (secret passed via $HEE_CRED_PASS env var, not argv, not printed)
3130fe4a82fd07f20a7f02b4e4021c2ac46206eb70dc7602b55a68aba3f97cd8

$ echo -n "s3kr1t-test-value-42" | sha256sum | cut -d" " -f1
3130fe4a82fd07f20a7f02b4e4021c2ac46206eb70dc7602b55a68aba3f97cd8
```

Hashes match — round trip is correct, and at no point does the real
value appear in this tool's own output.

## Real safety checks, all verified

```
$ echo "fake-piped-secret" | hee-cred -seal test@host -recipients x@y
hee-cred: -seal requires an interactive terminal -- refusing to read a secret from a pipe/redirect/script

$ hee-cred -pass nonexistent@host -exec echo hi
hee-cred: no sealed credential at .hee/secrets/nonexistent@host.gpg

$ hee-cred -pass spencer@kiosk
hee-cred: -exec <command...> required -- hee-cred never prints a decrypted secret directly
```

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
