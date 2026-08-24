# `hee-url` — real run

Real trigger: "./hee -url -short -sql 'thesis AND punk rock' -or -str
1976," then "no touch sb, we make. simple" -- deliberately fresh, not
built on the old gh/spencerbutler link-shortener-django project.
Deliberately kept to shorten/tag/search only, per Spencer's own
"simple. only simple. yes" -- the rg-scan/SQL-joins/elastic-style
relevance idea is real but a separate, bigger scope, tracked as its
own follow-up rather than bolted on here.

```
$ hee-url -short "https://tclug.org" -tags "thesis punk rock 1976 tclug"
hee-url: ab589e9 -> https://tclug.org  [thesis punk rock 1976 tclug]

$ hee-url -search thesis "punk rock"
ab589e9: https://tclug.org  [thesis punk rock 1976 tclug]

$ hee-url -search "nonexistent" "1976" -or
ab589e9: https://tclug.org  [thesis punk rock 1976 tclug]

$ hee-url -search "nonexistent-term-xyz"
hee-url: no match for 'nonexistent-term-xyz'
```

Real footgun caught mid-dogfood: a malformed test invocation (passing
`-search` twice) silently used only the second value -- not a tool bug,
but the failure-path error message was also a raw Python list repr at
the time; fixed to print clean joined text instead.

## Explicitly not built here

- No rg-scan integration, no SQL joins, no relevance scoring/fuzzy
  matching -- real, bigger idea, tracked separately, not built tonight
  given the hour.
