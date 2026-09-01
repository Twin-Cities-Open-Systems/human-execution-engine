# `hee-net -proto finger` — real run

Real trigger: "finger and gopher and snmp will be good buds" -- same
family of old, simple, text-based query protocols. `hee-net` was
already built with `-proto` as an extension point; finger is the
second real protocol on it.

```
$ hee-net -proto finger -query spencer
Login: spencer        			Name: Spencer Butler
Directory: /home/spencer            	Shell: /bin/bash
On since Fri Aug 21 16:46 (CDT) on pts/0 from 10.0.0.239
    ...
```

Local queries (`-query <user>`, no `@host`) shell out to the real
`finger(1)` client rather than reimplementing local session/`.plan`
lookup -- that's real, already-correct system behavior, not something
to duplicate. Remote queries (`-query user@host[:port]`) speak RFC 1288
directly over a raw socket, same shape as the gopher fetch.

Gopher re-verified working after this change (byte-identical to the
earlier run) -- the two protocols share `hee-net`'s dispatch, not
implementation.

## Explicitly not built here

- No remote fingerd exists yet to test the `user@host` path against a
  real server -- structurally correct per RFC 1288, not live-verified.
