# `qmail` -> `hee-procmail` wiring — planned, not yet dogfooded

Real trigger: [HEE#355](https://github.com/Twin-Cities-Open-Systems/human-execution-engine/issues/355)
-- `hee-procmail`'s own example (`examples/hee-procmail-output.md`)
explicitly deferred this: "no real MTA/mail-server wiring... that's
`mx-N.tcos.us`'s dependency, not this tool's." This is that dependency,
sketched out concretely so #355 has real code to build against instead
of just prose. **Illustrative, not dogfooded** -- qmail isn't installed
anywhere yet, so unlike the other `examples/*-output.md` docs this
isn't a real captured run.

## The chain

```
real SMTP connection
  -> qmail-smtpd (unprivileged UID, accepts the raw message)
  -> qmail-queue  (unprivileged UID, writes it to the local queue)
  -> qmail-local  (looks up the recipient's .qmail-* file)
  -> .qmail-gateway (a flat file, one instruction: pipe to a program)
  -> hee-procmail (this repo's tool, real stdin interface, unchanged)
  -> .hee/mailrules.yaml (the real rule file, already dogfooded)
```

Nothing about `hee-procmail` itself changes -- it already reads a raw
message on stdin exactly the way an MTA hands one off. qmail's job
here is entirely "be the thing that hands it off."

## `.qmail-gateway`

qmail's real local-delivery mechanism: a flat file named
`.qmail-<localpart>` in the recipient's home directory (or a
`.qmail-default` catch-all), where a line starting with `|` means
"pipe the raw message to this command" instead of delivering to a
mailbox. For every address under the `hee-irc+*`/etc. custom naming
scheme to land on `hee-procmail`, the real file is:

```
# ~alias/.qmail-gateway (or .qmail-default, if every custom-named
# address should route through hee-procmail rather than just one)
|/path/to/human-execution-engine/tooling/bin/hee-procmail -rules /path/to/.hee/mailrules.yaml
```

That's the entire integration surface. No adapter script, no format
conversion -- qmail's pipe delivery and `hee-procmail`'s stdin read are
the same real interface on both ends.

## Minimal install sketch (illustrative -- verify real package
availability per HEE#355's own open scope item before running any of
this for real)

```bash
# Real check first -- don't assume the package name/availability,
# qmail's packaging has historically been inconsistent across distros.
apt-cache search qmail 2>/dev/null || echo "not in apt -- check netqmail/notqmail source install instead"

# notqmail (the maintained fork) is the real current answer if apt
# comes up empty -- source build, own unprivileged users per binary,
# matching the privilege-separation point HEE#355 cites as the actual
# reason for choosing qmail over Postfix in the first place.
```

## Explicitly not solved here

- Which host (`pve` vs `nuc-1`) -- HEE#355's own open scope item, not
  decided by this example.
- Whether the separate `hee-mail-ingress.sh.md` thesis (GPG-verified
  SNMP command ingress) becomes a `hee-procmail` rule or a genuinely
  separate `.qmail-*` pipe -- same unreconciled question HEE#355 flags,
  repeated here so it isn't lost between the two docs.
- Real SMTP-level hardening (rate limiting, real spam filtering) --
  out of scope for "does the pipe work," a separate real pass once
  the wiring itself is proven.
