# prompts/PROMPTING_RULES.md

Real rules for how an agent should behave in this repo, not a placeholder.
The authoritative *policy* prose lives in `docs/doctrine/HEE_POLICY.md` —
this file is the compact, agent-facing summary an agent actually reads at
the top of a session, per `prompts/INIT.md`.

**This file is org-wide canonical, not just for this repo** — every other
TCOS repo's `CLAUDE.md` pulls it in via `@~/git/human-execution-engine/prompts/PROMPTING_RULES.md`.
That import is a **real, required assumption that every repo is checked
out under `~/git/<repo>`** (this org's own convention, per `bin/init-org.sh`'s
`WORKSPACE_DIR="${HOME}/git"`) — `~` is the most portable path form
Claude Code's `@import` actually supports (confirmed: no `$HOME`/env-var
expansion, no workspace-relative mechanism). On a machine that doesn't
follow that layout, the import silently fails to resolve and this file
won't be in context for other repos' sessions — if you're not sure it
loaded, read this file directly rather than assume it did.

## The rules

1. **Never commit or push directly to `main`.** All work happens on a
   branch and lands through a PR. Ordinary `git`/`gh` commands are fine
   on a branch — there is no wrapper to route through. Branch protection
   on `main` is the real control: server-side, so it binds every
   operator, agent and machine equally and cannot be bypassed by not
   calling a script. **Retired 2026-08-31**: `scripts/hee_git_ops.sh`,
   its CI presence check, and `HEE_TOOL_MODE`. The full reasoning is in
   `docs/guides/GIT_GH_WORKFLOW.md` — short version: `--reason` was
   required everywhere and never used by anything, `--act` plus
   `HEE_TOOL_MODE` were two flags from the same hand, the op set had no
   `merge`/`issue-create`/`rebase` so real work had no sanctioned path,
   rule 12 instructed agents to run a command rule 1 banned, and the CI
   check ran `continue-on-error: true` while only verifying that the
   script existed.
2. **Never fabricate.** No invented file references, no claimed-but-unrun
   commands, no asserted "landed"/"merged"/"done" without checking the
   actual state first. Includes the subtler form: never redirect stderr
   to `/dev/null` (or otherwise discard an exit code) and then interpret
   the resulting silence as a real negative result — check *why* a
   command produced no output before reporting what that silence means
   — HEE Policy §6.
3. **Reference issues and PRs as a short label linked to the full URL**:
   `[repo#N](https://github.com/<owner>/<repo>/(issues|pull)/<n>)`. Short
   to read, and the URL travels with it. **Measured, not inferred** --
   operator probe 2026-08-31, four candidate forms tested live in both a
   terminal and a browser:
   - `repo#N` alone and `owner/repo#N` alone link **nowhere** outside a
     GitHub conversation. The owner-less form resolves nowhere at all,
     even inside GitHub (verified against GitHub's own renderer).
   - A bare full URL works everywhere but is **too long to read** in
     chat -- the operator's own verdict on seeing it.
   - **OSC 8 terminal hyperlinks are impossible from an agent's chat
     output.** The ESC bytes are stripped in transit, silently
     concatenating URL and label into one broken string that 404s.
     Do not attempt it. Tools writing straight to a TTY are unaffected
     and *should* emit OSC 8.
   - The linked short label renders correctly in both surfaces. It is
     not click-through in the terminal -- a renderer limitation nothing
     in this repo can fix -- but it is the best form that exists today.
   Exceptions, because the renderer differs:
   - **Repo `.md` files**: bare full URL. Nothing autolinks in files, so
     a short label has nothing to fall back on.
   - **Structured work files** (contracts/blueprints/doctrine YAML):
     `issue:N@repo` / `pr:N@repo` -- §13. Machine-parsed, no renderer.
   Rewritten twice in one day from inference before being settled by
   measurement. Do not relitigate without new measurements.
4. **Self-assign what you create, label from the existing set, never
   invent a new label** — **HEE Policy §10/§12.** **Merge authority,
   relaxed 2026-08-31**: a PR merges when its checks pass and its
   assignee is satisfied. A PR carrying the **`human`** label requires
   explicit human approval before merge; no other PR does. The former
   "only the opener closes/merges" rule is retired — it produced
   confusion without a matching risk, and contradicted §10's own text.
   Tighten again only once the workflow is stable and the tightening
   earns its cost.
5. **When in doubt, stop and ask rather than guess** — same invariant as
   below, restated because it's the one that matters most.
6. **Target GNU tool syntax/behavior by default**, not BSD or another
   implementation — real, not stylistic (`sed -i` requires an explicit
   suffix argument on BSD, optional on GNU; `date -d` is GNU-only) —
   HEE Policy's GNU Tools Preference Policy.
7. **When a doc's stated design contradicts real precedent already in
   use, surface both sides and reconcile — don't silently pick one.**
   Review why the old standard existed and why current practice
   diverged, reason toward the best of both rather than a unilateral
   pick, let the human decide on a genuine tradeoff, then canonize the
   resolution back into the doc with its reasoning kept — HEE Policy
   §19.

8. **Commit format and merge flow.** Conventional Commits
   (`type(scope): concise imperative description`; `feat`/`fix`/`chore`/`docs`)
   for every commit and PR title. Merge via `gh pr merge --squash`; add
   `--delete-branch` only for `feature/`-prefixed branches -- `touchy/`-prefixed
   branches are kept post-merge as an audit trail by design (see HEE Policy
   §2). Absorbed from the org's old `WORKFLOW.md`, 2026-08-27.
9. **Issue hierarchy.** Epic (org roadmap, multi-repo, spans quarters) ->
   Feature (one discrete capability) -> Sub-issue (PR-bound tactical work,
   keeps its own labels -- labels don't inherit from the parent).
10. **Three real footguns, absorbed from the org's old
   `ORGANIZATION_BOOTSTRAP.md`, 2026-08-27:**
   - Never run a destructive git clean (`git clean -fdx`, `git reset --hard`)
     immediately after a `git stash pop` in a multi-repo/headless script --
     the just-popped changes sit uncommitted and get purged as noise. Use
     `pull --rebase` or an isolated branch instead of a trailing reset.
   - Any pre-commit hook that runs `git diff`/`git status` internally needs
     a recursion guard (`TCOS_HOOK_RUNNING` env var, checked and set at the
     top, `exit 0` if already set) -- without it, the hook re-triggers
     itself until the shell hits its subshell-depth limit and crashes.
   - Never hardcode a real user's home path (`/home/spencer/...`) into a
     shared init/bootstrap script or template -- use `$HOME` so it works on
     any machine, user, or automated node.
11. **Color/status output goes through the Claude Code `dataviz` skill's
    rules, always -- never bare red/green.** Real trigger, 2026-08-28: an
    agent session built a plain ✅/❌ status table (and had been echoing
    hee-view's 🔴/🟡/🟢 dots uncritically all session) before ever loading
    the skill. Spencer, direct: "this red is anti spencer." Status colors
    (good/warning/serious/critical) ship with an icon + label, never color
    alone, and any real palette gets run through the skill's
    `scripts/validate_palette.js` before shipping -- see `UI_UX_REVIEW.md`/
    `STATUS_AND_PRIORITIES.md` in `thesis-engine` for prior real findings
    from the same validator. Applies org-wide, not just chart code: plain
    chat/table output using red/green as the only distinguishing cue is
    the same failure mode.
12. **Every issue gets every real field filled at file-time, not just a
    title and body** -- HEE Policy §18. When running `gh issue create`,
    set `--label` plus the real issue type (Task/Bug/Feature/Epic/
    Incident) and any project fields (Priority, Effort, Target-Date) the
    same session, never deferred to a "backfill later." Real trigger,
    2026-08-29: Spencer caught three issues filed this session
    (issue:335@fleet-ops, issue:421@human-execution-engine,
    issue:36@resume) with zero fields set beyond title/body -- same
    repeated mistake §18 already names. Use
    `tooling/bin/hee-fields set --repo <owner>/<repo> --number <N>
    --type <T> --priority <P> --effort <E>` -- **`--repo` needs the full
    `owner/repo` form**, a bare repo name 404s silently confusing (real
    footgun hit fixing this same session).
13. **New tools start at the least-capable language that does the real
    job, and graduate only when actually outgrown** -- HEE Policy §21,
    the tool-maturity ladder: `library/bash/*.shfn.bash` (sourced
    function) -> `tooling/bin/*` sh/bash (standalone script) ->
    `tooling/bin/*.py` (real parsing/data structures needed) -> a real
    `hee` subcommand (`cmd/hee/`, not built yet for most tools) -> Go/
    Rust/C only once a tool has actually outgrown Python. Never start a
    new tool at a heavier language "to be safe" or "for consistency."
    Real, working convention all session before it was ever written down
    as policy (`hee-repo-refresh`/`hee-check-og` as `sh`, `hee-fields` in
    Python) -- previously documented only in `docs/guides/OPERATOR_GUIDE.md`,
    not governance. Spencer, direct, 2026-08-29: "our programing
    convention should be in governance, confirm."
14. **Default to Status Block for any multi-item progress/status report**:
    short bulleted lines, each prefixed with an icon+label status marker
    (✅/⏳/❌ or equivalent -- never a bare color, consistent with rule
    11's dataviz-skill requirement), a short linked label for every
    issue/PR reference per rule 3 -- `[repo#N](full-url)`, never bare
    shorthand and never a naked URL -- no narrative padding around the
    list -- see the
    `Status Block` glossary term (`.github/profile/GLOSSARY.md`) for the
    real precedent this codifies. General chat-output convention, not
    scoped to this repo.

15. **Check the existing `hee-*` tools first. Extend one. Never write a
    one-off.** Before building anything, run `hee list` (or look in
    `tooling/bin/`) and find the tool this belongs to. Add a subcommand or
    a mode to that tool. A new top-level `hee-<cmd>` is a last resort and
    needs a real reason -- closely-related functionality folded into an
    existing tool beats a sibling command every time. A script written
    outside the `hee` surface, used once and left in a session transcript,
    is not a deliverable: nobody else can find it, run it, or maintain it.
    Applies equally to shell helpers and Python: put the logic in
    `library/` where it is testable and reusable, and keep the tool itself
    thin. Spencer, direct, 2026-08-31: "must make sure you check current
    hee tools and use, expand never one off. this must be mandated
    governance and avail on startup." Real trigger the same session: an
    agent was about to write a standalone doc-reference checker before
    being told to extend `hee-check` instead -- which is where it now
    lives, as `hee-check refs`.

16. **Two layers of CI: ours for what's ours, standard for what's
    standard.** Every repo runs `hee-check all` -- it needs no toolchain,
    no language runtime, and catches org-specific rot nothing else looks
    for (broken file references, hardcoded `/home/<user>/` paths, derived
    state committed to git, invalid systemd units). On top of that, run the
    standard tool for each language actually present: `shellcheck` for
    shell, `ruff` for Python, `cargo clippy`/`fmt`/`test` for Rust, the
    project's own test runner for JS.

    **Never write a TCOS version of a tool that already exists.** A hee
    tool earns its place only when the check is about something no external
    tool can know -- `hee-lint` validates HEE object envelopes, `hee-view`
    checks our sitemap against our hosts. Nobody should write a TCOS Python
    linter; that is what `ruff` is.

    **Call org tooling by checking out its home repo, never by vendoring a
    copy.** `.github`'s site-health workflow is the pattern. Real trigger,
    2026-08-31: vendoring produced three files named `security_scanner.py`
    across three repos, doing two different jobs, all diverged
    (issue:468@human-execution-engine).

    **A CI job's name must not claim provenance its code does not have.**
    Same trigger: `MT-logo-render` had jobs called "HEE Security Scan" and
    "HEE Recipe Validation" that ran repo-local Python. A name implying a
    shared standard is being enforced, when none is, is worse than no name.

    **Never add a check that is red on day one.** If it finds real
    pre-existing problems, land it `continue-on-error` WITH the reason and
    the flip condition written in the workflow, and a ticket. A
    permanently-red check trains people to ignore red -- measured cost:
    `.github`'s site-health was red on 14/14 hosts every 30 minutes for
    weeks, and a genuine outage would have been invisible in it
    (issue:350@fleet-ops).

17. **Manuals are part of the change, not a follow-up.** A tool's `--help`
    IS its man page -- `hee-gen-manpages` derives every generated page from
    it -- so help text that is broken, stale or absent publishes exactly
    that to `man.tcos.us`. Real cost, measured 2026-08-31: the live
    `hee-check` page read `find: unknown predicate '--help/prompts'` for
    weeks. This project's own bug report, served as its documentation.

    Concretely, in the same change that touches a tool:
    - **Declare the section.** Every tool carries `# section: N` in its
      header -- 1 for a user command, 8 if it CHANGES host or system state,
      5 for a file format, 7 for a convention, 3 for a library. `hee check
      cli` warns when it is missing. A central map was considered and
      rejected: it goes stale the moment someone forgets to register a new
      tool, while a header line travels with the code.
    - **Regenerate.** `hee gen-manpages` after any change to a tool's help,
      and `--gopher` when the published tree needs rebuilding. **Both are
      dry runs until you add `--write`** -- a bare run reports what would
      change and writes nothing, because a documentation generator that
      mutates the tree on a bare invocation once installed a pre-commit hook
      as a side effect (issue 464).
    - **Never hand-edit a generated page.** Fix the tool's help, or the
      generator. Hand-editing is how `man/hee.1` came to document six <!-- hee-check:refs-ok  that page was removed by #484; repointing this path would make the example describe a file that never had the problem -->
      subcommands that no longer exist.

    Authored pages under `man/manN/` win over generated ones and are the
    right home for anything not derived from `--help`. Man pages are read
    straight out of the checkout via `MANPATH` (`make manpath` in dotfiles)
    -- never copied or installed, so `git pull` is the update mechanism and
    there is no second copy to drift.

## Authority Invariants

- Authority is scoped to this repository and this workflow context.
- No external side effects without explicit operator action.
- When in doubt: stop; do not guess.

## Scope Invariants

- Scope is limited to this repository and this workflow context.
- No external side effects without explicit operator action.
- When in doubt: stop; do not guess.

## Invariants

- Do not violate repository invariants.
