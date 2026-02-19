# Privacy Leak Scrub Playbook (GitHub)

Purpose: remove a file path from Git history after an incorrect emit to the incorrect repo, and harden procedures to prevent recurrence.

## Severity ladder (p0–p4)

- p4: cosmetic / metadata only (non-sensitive, already public)
- p3: personal info not intended for public consumption (name/title/contact); no credentials
- p2: credential-like or private business data; rotate + scrub
- p1: secrets with credible exposure (tokens, keys); immediate rotation + scrub + audit
- p0: active compromise or high-impact secrets; rotate + scrub + incident response + containment

## Correct action (GitHub.com)

1) Precheck (mirror clone + evidence):
- `hee/library/sh/hee-scrub-precheck.sh --repo-slug <owner/repo> --leak-path <path>`

1) Apply scrub (history rewrite + force push):
- requires `git-filter-repo`
- `hee/library/sh/hee-scrub-apply.sh --repo-slug <owner/repo> --leak-path <path> --workdir <from precheck>`

1) Verify:
- `hee/library/sh/hee-scrub-verify-remote.sh --repo-slug <owner/repo> --leak-path <path>`

## GitHub Support (cached PR diffs / refs/pull/*)

If mirror verification retains the filename, it is reachable via GitHub-managed PR refs/caches.
A Support purge is required for full removal from PR diff views and hidden refs.

## Notes

- “Correct action” is evidence-driven: verify normal clone surface AND mirror surface.
- Avoid PWD-based emits. Always prove identity before emit.
