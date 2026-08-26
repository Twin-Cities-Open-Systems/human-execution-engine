# uiboss(1)

```
uiboss

USAGE:
  uiboss ls
  uiboss run <action-id> [args...]
  uiboss serve [--bind IP] [--port N]

ENV:
  UIBOSS_ACTIONS_DIR  default: ~/.hee/uiboss/actions.d
  UIBOSS_SITE_ROOT    default: ~/.hee/uiboss/site

NOTES:
  - run captures output to a run dir and generates HTML
  - serve hosts SITE_ROOT via python -m hee_webserver
```
