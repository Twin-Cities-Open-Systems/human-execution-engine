# `hee-scrob` — status

Real trigger: "terse and hee and very spencer for when I /scrob in
#tclug," then extended same conversation to include year, playback
timestamp, and the real subtitle line active at that position (sourced
from real `.srt` files in `/mnt/nuc1-pool/media/`, never invented).

## What's verified for real

- The no-token safety path: `PLEX_TOKEN` unset → clean error, exit 1.
- Syntax valid (`ast.parse`).
- Real `.srt` files in the media library match the format the parser
  assumes (checked directly against
  `Movies/2021-King_Richard/King_Richard-....en.srt`).

## What's NOT verified

No `PLEX_TOKEN` exists in this environment, so the actual live fetch
against `plex.crooked.tcos.us` and the full SRT-lookup-at-real-offset
path haven't been exercised end to end against a real playing session.
Real gap, not hidden -- once a token's sealed via `hee-cred`
(`hee cred -pass plex-token -exec hee-scrob`), this needs one real
dogfood run against whatever's actually playing to confirm the Plex
XML field names match what this expects (`grandparentTitle`,
`parentTitle`, `parentYear`, `viewOffset`, `Media/Part/@file`) -- these
are documented Plex API fields, not guessed, but documented and
observed-in-the-wild aren't the same thing.

## Wiring, once trusted

```
# in ~/.irssi/config aliases block:
SCROB = "EXEC -o ~/.local/bin/hee-scrob";
```

Then `/scrob` in any channel posts the real now-playing line directly.
