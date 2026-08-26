# `hee-lg` — real run

Real trigger, 2026-08-21/22: researching Honeycomb Internet Services
(AS25720, honeycomb.net) for a possible TCOS deploy/hosting partnership
meant hand-running whois, RIPEstat, and PeeringDB lookups in sequence.
Spencer named the class of tool ("looking glass") and asked for it as a
real command — `./hee lg honeycomb.net`. Dogfooded against that exact
target, not a synthetic one.

```
$ ./hee lg honeycomb.net
hee-lg: honeycomb.net -> 204.246.83.177 -> AS25720
  holder: HONEYCOMB - Honeycomb Internet Services
  announced now: 10 IPv4 / 2 IPv6 prefixes
  peeringdb: policy='Open' scope='Regional' type='Content'
  looking glass: (none published)

$ ./hee lg AS25720
hee-lg: AS25720 -> AS25720
  holder: HONEYCOMB - Honeycomb Internet Services
  announced now: 10 IPv4 / 2 IPv6 prefixes
  peeringdb: policy='Open' scope='Regional' type='Content'
  looking glass: (none published)
```

Both entry points (domain and bare `AS<N>`) converge on the same real
data, sourced live from three independent public APIs (Team Cymru whois,
RIPEstat, PeeringDB) — no scraping, no API keys required.

## Explicitly not built here

- No geo/facility listing (PeeringDB's `netfac` endpoint has it, one more
  real call away) — left out of this first cut, not forgotten.
- No caching — every run is a live lookup. Fine for the low call volume
  this is used at; worth revisiting if that changes.
- `looking glass` field reports what the network itself published to
  PeeringDB, which can be empty (as with AS25720 here) even when a real
  looking glass exists elsewhere and just isn't listed there.
