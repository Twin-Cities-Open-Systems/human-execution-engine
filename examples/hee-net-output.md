# `hee-net` — real run

Real trigger: Chrome dropped native `gopher://` support years ago --
"chrome no first try." Fetched `gopher://gopher.quux.org:70/1/Software/Gopher`
directly via a raw socket first, then wrapped into a real, reusable tool.

```
$ ./hee net -proto gopher -url "gopher://gopher.quux.org:70/1/Software/Gopher"
iTHE GOPHER PROJECT	/Software/Gopher/fake	gopher.quux.org	70
i------------------	/Software/Gopher/fake	gopher.quux.org	70
...
1Clients, Servers, and Downloads	/Software/Gopher/Downloads	gopher.quux.org	70	+
1Major Gopher Servers	/Software/Gopher/servers	gopher.quux.org	70	+
1Using Gopher	/Software/Gopher/using	gopher.quux.org	70	+
```

Output matches a raw manual fetch byte-for-byte.

## Explicitly not built here

- Only gopher today (`-proto` takes one choice) -- the flag shape is
  there for whatever real protocol comes next, not a promise of a
  general-purpose fetcher.
- No item-type-aware rendering (menu vs text vs binary) -- prints the
  raw response either way. Real gopher clients render menus as
  navigable lists; this is a fetch tool, not a browser.
