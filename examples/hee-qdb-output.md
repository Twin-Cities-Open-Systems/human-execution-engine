# `hee-qdb` — real run

Real trigger: "so I can /qdb that shit in irc and get the quote from
you however, not central, is chaos entropy tool too" -- deliberately
not one canonical quote database, searches across multiple real source
files, picks randomly among matches.

Dogfooded against the real, existing quote in
`fleet-ops/WHO-WE-ARE.md`'s Quotes section:

```
$ hee-qdb -search "counting fact" -source WHO-WE-ARE.md
"because it's not a search problem, it's a counting fact." -- touchy-claude, 2026-08-18

$ hee-qdb -search "totally not real string xyzzy" -source WHO-WE-ARE.md
hee-qdb: no match for 'totally not real string xyzzy' across 1 source(s)
```

Real footgun caught and fixed mid-build: the source markdown wraps long
quotes across multiple lines, and the first pass leaked that raw
line-wrap whitespace straight into the output. Fixed by normalizing
whitespace on extraction, re-verified against the same real quote.

## Explicitly not built here

- Only one real source wired by default (`WHO-WE-ARE.md`) -- `-source`
  can be repeated for more, but no second real quote-bearing file
  exists yet to test multi-source behavior against.
- No fuzzy/typo-tolerant matching, substring only.
