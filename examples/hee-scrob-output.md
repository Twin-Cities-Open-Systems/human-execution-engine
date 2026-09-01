# `hee-scrob` — real run

Real trigger: "terse and hee and very spencer for when I /scrob in
#tclug," then extended same conversation to include year, playback
timestamp, and the real subtitle line active at that position (sourced
from real `.srt` files next to the media file, never invented).

## What's verified for real (2026-08-29 pass)

`format_line()` and `read_token()` loaded directly via
`importlib.machinery.SourceFileLoader` (the file has no `.py`
extension) and exercised with synthetic, non-live data — no real Plex
server involved in this fixture.

```
$ python3 -c "
import importlib.machinery, importlib.util, os
loader = importlib.machinery.SourceFileLoader('hee_scrob', 'tooling/bin/hee-scrob')
spec = importlib.util.spec_from_loader('hee_scrob', loader)
mod = importlib.util.module_from_spec(spec)
loader.exec_module(mod)

track = {'kind': 'track', 'artist': 'UK Subs', 'title': 'Artificial', 'album': 'Yellow Leader', 'year': '2015', 'ts': '00:00:47', 'device': 'Chrome'}
print('TRACK:', mod.format_line(track))

video = {'kind': 'video', 'title': 'The Sopranos s01e01 - The Sopranos', 'year': '1999', 'ts': '00:05:12', 'line': 'Whadda ya want from me?', 'device': 'LG TV'}
print('VIDEO:', mod.format_line(video))

video2 = {'kind': 'video', 'title': 'King Richard', 'year': '2021', 'ts': '01:22:03', 'line': None, 'device': None}
print('VIDEO(bare):', mod.format_line(video2))

os.environ.pop('PLEX_TOKEN', None); os.environ.pop('HEE_CRED_PASS', None)
print('no-env:', repr(mod.read_token()))
os.environ['HEE_CRED_PASS'] = 'from-hee-cred'
print('HEE_CRED_PASS-only:', mod.read_token())
os.environ['PLEX_TOKEN'] = 'from-plex-token-env'
print('PLEX_TOKEN-priority:', mod.read_token())
"
TRACK: np: UK Subs - Artificial (2015) [Yellow Leader] @ 00:00:47 (Chrome)
VIDEO: np: The Sopranos s01e01 - The Sopranos (1999) @ 00:05:12 -- Whadda ya want from me? (LG TV)
VIDEO(bare): np: King Richard (2021) @ 01:22:03
no-env: ''
HEE_CRED_PASS-only: from-hee-cred
PLEX_TOKEN-priority: from-plex-token-env
```

Confirms: `format_line()` correctly omits the device suffix and the
`-- line` suffix when either is absent (real, not fabricated —
`VIDEO(bare)` has neither), and `read_token()`'s real fallback order is
`PLEX_TOKEN` > `HEE_CRED_PASS` > plaintext file, matching the tool's
own documented contract after the 2026-08-29 fix
(https://github.com/Twin-Cities-Open-Systems/human-execution-engine/pull/428)
that made `HEE_CRED_PASS` actually work.

## What's NOT verified

No live Plex server in this environment — the actual live fetch
against a real Plex instance, and the full SRT-lookup-at-real-offset
path, haven't been exercised end to end against a real playing
session in *this* fixture run. Real gap, not hidden. (This has been
verified live in real usage outside this fixture — see the tool's own
commit history — but that live verification isn't reproducible here
without a real server.)

Discord posting (`-discord` flag, `post_discord()`) is similarly not
exercised here — it needs a real webhook URL, sealed via `hee-cred`,
and posting a real test message to a real Discord channel is a live
side effect this fixture deliberately doesn't perform.

## Wiring, real and generic (not an absolute path)

```
$ hee cred -pass plex-token -exec hee scrob
```

Routes through the `hee` dispatcher (`hee scrob` → `hee-scrob`) rather
than a hardcoded path like `~/.local/bin/hee-scrob`, so the same real
command works regardless of which machine/homedir it's run from — real
fix, 2026-08-29, after an earlier irssi-alias suggestion baked in an
absolute repo path.

In `~/.irssi/config`'s aliases block:

```
SCROB = "EXEC -o hee cred -pass plex-token -exec hee scrob";
```

Then `/scrob` in any channel posts the real now-playing line directly
— verified end to end, live, same session
(https://github.com/Twin-Cities-Open-Systems/human-execution-engine/pull/431
removed a debug line that had been leaking into the channel alongside
the real `np:` line).
