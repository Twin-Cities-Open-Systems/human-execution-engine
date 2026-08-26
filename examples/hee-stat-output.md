# `hee-stat` — real run

Real trigger, 2026-08-21: Spencer's `./hee stat -c %REPO gh/spencerbutler`.
`stat(1)`'s interface convention (`-c FORMAT`), applied to a namespaced
resource (`gh/...`) instead of the filesystem — not a fork of GNU
coreutils' `stat.c`, a new `hee` subcommand reusing the same mental
model.

## The exact invocation that started this

```
$ ./hee stat -c %REPO gh/spencerbutler
(empty line)
```

Correct, not a bug: `gh/spencerbutler` is a **user** path (no repo
component), so `%REPO` legitimately has nothing to show. Confirmed
deliberately, not assumed:

```
$ ./hee stat -c "[%REPO]" gh/spencerbutler
[]
```

## Real stat(1) semantics, reused rather than reinvented

```
$ ./hee stat -c "n=%n U=%U W=%W Y=%Y s=%s" gh/spencerbutler
n=spencerbutler U=spencerbutler W=1375241892 Y=1787184337 s=13

$ TZ=GMT date -d @1375241892
Wed Jul 31 03:38:12 AM GMT 2013   # real GitHub account creation date

$ TZ=GMT date -d @1787184337
Thu Aug 20 12:05:37 AM GMT 2026   # real last-activity date
```

`%W` (birth time) and `%Y` (mtime) are `stat`'s own real specifiers,
carrying the same semantic meaning here as they do on a real file —
just answering "when was this GitHub identity created / last active"
instead of "when was this file created / last modified."

## A real repo, using the TCOS convenience aliases

```
$ ./hee stat -c "n=%n REPO=%REPO ORG=%ORG W=%W" gh/Twin-Cities-Open-Systems/primitives
n=Twin-Cities-Open-Systems/primitives REPO=primitives ORG=Twin-Cities-Open-Systems W=1787338054
```

## Open, not yet built

Only the `gh/` namespace exists. Spencer's own framing was "explore
forking for our purposes" more broadly — other namespaces (`fs/` for
real filesystem passthrough through the same `-c FORMAT` interface,
maybe others) could follow the same pattern once there's a real second
use case, not built speculatively here.
