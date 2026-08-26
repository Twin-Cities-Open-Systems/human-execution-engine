# hee-print(1)

```
usage:
  hee-print [--no-header] [--] <file>...
  hee-print [--no-header] --stdin [--hint md|yaml|json|text]

behavior:
  .md/.markdown -> glow -p (if available)
  .yml/.yaml    -> yq -P   (if available)
  .json         -> jq .    (if available)
  other         -> bat/batcat -p --paging=never (if available) else cat
```
