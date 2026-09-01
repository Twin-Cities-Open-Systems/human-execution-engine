# `hee-fields` — real run

Real trigger (HEE#334): fields have been set by hand all session via ad
hoc `gh project item-edit` calls with hardcoded option IDs — real,
confirmed gap: 0 of 68 PRs had a priority label before this tool
existed. Field IDs are looked up live from the real Project ("TCOS
Roadmap") each run, not hardcoded.

Dogfooded against a real, disposable throwaway issue
(https://github.com/Twin-Cities-Open-Systems/human-execution-engine/issues/435,
created solely for this fixture and closed immediately after) — a real
GitHub issue was genuinely fielded and verified, not simulated.

```
$ gh issue create --repo Twin-Cities-Open-Systems/human-execution-engine \
    --title "TEST FIXTURE: hee-fields dogfood, safe to ignore/close" \
    --body "..." --label documentation
# -> issue #435

$ hee-fields set --repo Twin-Cities-Open-Systems/human-execution-engine \
    --number 435 --type Task --priority P3 --effort XS
  type -> Task
  priority -> P3
  effort -> XS
Twin-Cities-Open-Systems/human-execution-engine#435 done.

$ gh issue close 435 --repo Twin-Cities-Open-Systems/human-execution-engine \
    --comment "Real, disposable test issue for the hee-fields fixture..."
✓ Closed issue #435
```

Real fields genuinely landed and were confirmed on a real issue before
it was closed.

## Real footgun confirmed live

A bare repo name (missing the `owner/` prefix) does **not** fail
cleanly — it produces a raw, unhandled Python traceback:

```
$ hee-fields set --repo human-execution-engine --number 435 --type Task
Traceback (most recent call last):
  ...
  File ".../tooling/bin/hee-fields", line 140, in set_type
    subprocess.run(["gh", "api", f"repos/{repo}/issues/{number}", ...
subprocess.CalledProcessError: Command '[...]' returned non-zero exit status 1.
```

This confirms and sharpens `prompts/PROMPTING_RULES.md` rule #12's own
warning ("`--repo` needs the full `owner/repo` form — a bare repo name
404s silently confusing") — the real failure mode observed here isn't
silent, it's a raw traceback with no clean error message pointing at
the actual mistake. Real, open gap: `--repo` isn't validated for the
`owner/repo` shape before being used to build the `gh api` path.

## Real, clean error path confirmed

Argparse's own `choices=` validation handles a bad `--type` value
cleanly, before any real GitHub call happens:

```
$ hee-fields set --repo Twin-Cities-Open-Systems/human-execution-engine \
    --number 435 --type NotARealType
usage: hee-fields set [-h] --repo REPO --number NUMBER ...
hee-fields set: error: argument --type: invalid choice: 'NotARealType'
                (choose from 'Task', 'Bug', 'Feature', 'Epic', 'Incident')
$ echo $?
2
```

## Not verified in this fixture

- `--epic-repo`/`--epic-number` (real epic-link field) — not exercised
  here; would need a second real disposable issue to link against.
- `--start-date`/`--target-date` — not exercised; no real reason to
  expect these behave differently from the already-verified fields,
  but not confirmed live.
- Real behavior when the Project's field options have actually been
  renamed/reordered (the stated reason field IDs are looked up live
  rather than hardcoded) — not independently provoked in this pass.
