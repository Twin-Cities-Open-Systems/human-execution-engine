# hee(1)

```
hee — tiny router (POSIX sh)

usage:
  hee lint [--mode warn|error]
  hee hooks install [--repo <path>]
  hee git merge [-r <regex>] [--squash|--merge|--rebase] [--org <org>] [--author <login>]
  hee help

design:
  - TOOL root comes from this script location
  - TARGET root comes from current git repo (cwd)
  - extension: hee <cmd> tries tooling/bin/hee-<cmd> in target repo first, then tool repo
```
