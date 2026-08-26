# hee-git-merge(1)

```
usage: hee-git-merge [-h] [-r REGEX] [--org ORG] [--author AUTHOR]
                     [--action {merge,approve,batch,optimize,prime}]
                     [--batch-size BATCH_SIZE] [--squash | --merge | --rebase]
                     [--delete-branch | --no-delete-branch] [--no-cache]

options:
  -h, --help            show this help message and exit
  -r REGEX, --regex REGEX
  --org ORG
  --author AUTHOR       filter by login, or 'all' for every open PR org-wide
  --action {merge,approve,batch,optimize,prime}
  --batch-size BATCH_SIZE
                        max PRs per batch under --action batch (default 5)
  --squash
  --merge
  --rebase
  --delete-branch
  --no-delete-branch
  --no-cache            skip the 60s PR-detail cache, always fetch live (e.g.
                        right before an actual merge)
```
