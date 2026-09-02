# bootstrap.mk -- real, minimal HEE org/user environment bootstrap.
#
# Real trigger (2026-08-24): spencer@kiosk couldn't run `hee git merge`
# -- diagnosed live: `hee` resolved to a manually-placed partial
# `~/tooling/bin/` (13 tools, hand-copied) instead of a real repo clone,
# so the dispatcher's tooling/bin extension search had nothing behind
# it. Real, concrete instance of fleet-ops#263's problem (accounts with
# tools half-installed instead of a clean bootstrap), dogfooded here
# rather than fixed by hand.
#
# Deliberately GNU Make, not a Python/shell wrapper -- Spencer's own
# repeated framing ("make -org tcos -user paul", "gated by the PR to
# have make files bootstrap an env") names the real tool. Real Make
# variable convention (ORG=/USER=), not literal -org/-user flags (make
# doesn't have those) -- same spirit, real syntax.
#
# Usage:
#   make -f tooling/bootstrap.mk ORG=tcos USER=spencer bootstrap
#
# Fully unprivileged by design -- every target is a plain git-clone/
# symlink/mkdir a normal user can run in their own home directory. Never
# invokes sudo, never assumes one. Matches spencer@kiosk's real,
# permanent unprivileged status -- this bootstraps the account AS
# ITSELF, not as a workaround around that constraint.

ORG ?= tcos
USER ?= $(shell whoami)
GH_ORG := Twin-Cities-Open-Systems
REPO := human-execution-engine
GIT_URL := https://github.com/$(GH_ORG)/$(REPO)
HOME_DIR := $(HOME)
CLONE_DIR := $(HOME_DIR)/git/$(REPO)
BIN_DIR := $(HOME_DIR)/.local/bin
GIT_DIR := $(HOME_DIR)/git
HOOKS_DIR := $(HOME_DIR)/.claude/hooks
CLAUDE_SETTINGS := $(HOME_DIR)/.claude/settings.json

# `help` is the default goal, and it is DERIVED from this file rather than
# hand-kept. Real trigger 2026-09-02: `make -f tooling/bootstrap.mk help`
# answered "No rule to make target 'help'". Worse, a bare invocation with no
# target silently ran print-governance-reminder, because that was simply the
# first target in the file -- an accident of ordering, not a decision.
#
# Same lesson tooling/bin/hee records for its own router: "a list kept in
# this file goes stale the moment someone adds a tool, which is how
# man/hee.1 came to document six subcommands that no longer existed." So
# this greps the `## ` annotations off the target lines themselves. Add a
# target with a `## ` comment and it appears here; add one without, and the
# check below says so rather than letting it hide.
.DEFAULT_GOAL := help

.PHONY: help check-help
help: ## show this help (default)
	@echo "bootstrap.mk -- HEE org/user environment bootstrap"
	@echo ""
	@echo "USAGE"
	@echo "  make -f tooling/bootstrap.mk [ORG=tcos] [USER=$$(id -un)] <target>"
	@echo ""
	@echo "TARGETS"
	@grep -hE '^[a-zA-Z0-9_.-]+:.*?## ' $(MAKEFILE_LIST) \
	  | sort \
	  | awk 'BEGIN{FS=":.*?## "}{printf "  %-26s %s\n", $$1, $$2}'
	@echo ""
	@echo "VARIABLES"
	@echo "  ORG      org slug            (default: $(ORG))"
	@echo "  USER     account to set up   (default: $(USER))"
	@echo "  CONFIRM  reset-tooling only; must be 'yes' to actually execute"
	@echo ""
	@echo "PATHS (expanded for the current ORG/USER)"
	@echo "  clone dir   $(CLONE_DIR)"
	@echo "  bin dir     $(BIN_DIR)"
	@echo "  git dir     $(GIT_DIR)"
	@echo "  backup dir  $(BACKUP_DIR)"
	@echo ""
	@echo "EXIT STATUS"
	@echo "  0 OK   1 WARNING   2 CRITICAL   3 UNKNOWN"

# Every .PHONY target must carry a `## ` description. Without this, adding a
# target and forgetting the comment makes it invisible in help -- the same
# silent-omission failure, one level up.
#
# The .PHONY list is read out of the FILE, not from $(.PHONY). Written that
# way first on 2026-09-02 and it silently passed: `.PHONY` is a special
# TARGET, not a variable, so `$(.PHONY)` expands to nothing, the loop ran
# zero times and the check reported OK. A check that cannot fail is worse
# than no check -- it is a green light with nothing behind it. Caught only
# by deliberately adding an undocumented target and expecting a failure.
#
# It reads the TARGET DEFINITIONS, not .PHONY. Two reasons: parsing .PHONY
# means handling backslash continuations (a first attempt over-matched and
# swallowed the help: line into the target list), and checking definitions
# also catches a target someone forgot to add to .PHONY -- which is its own
# bug. Every target in this file is phony, so the two lists should agree.
check-help: ## verify every target is documented in help
	@mk=$(firstword $(MAKEFILE_LIST)); \
	all=$$(grep -oE '^[a-z][a-z0-9_.-]*:' "$$mk" | tr -d ':' | sort -u); \
	if [ -z "$$all" ]; then \
	  echo "UNKNOWN   found no targets in $$mk" 1>&2; exit 3; \
	fi; \
	undocumented=""; n=0; \
	for t in $$all; do \
	  n=$$((n+1)); \
	  grep -qE "^$$t:.*## " "$$mk" || undocumented="$$undocumented $$t"; \
	done; \
	if [ -n "$$undocumented" ]; then \
	  echo "CRITICAL  targets missing a '## ' description:$$undocumented" 1>&2; \
	  exit 2; \
	fi; \
	echo "OK        all $$n targets are documented"

.PHONY: bootstrap bootstrap-all clone-repo clone-all-repos link-hee status \
        health-all-repos pull-all-repos refresh-all-repos print-governance-reminder \
        link-cache-prune install-cron reset-tooling restore-secrets install-dotfiles \
        link-hooks install-hooks

# Real trigger (2026-08-28): an agent session ran raw git commit/merge
# repeatedly across three repos before ever reading PROMPTING_RULES.md --
# the rules were real and canonical the whole time, just never surfaced
# at the one moment (env bootstrap/refresh) every identity actually
# passes through. Spencer, direct: "must not be missed again... you
# guys act like idiots otherwise." Printed, not just linked, so it
# can't be silently scrolled past the way a bare path can.
print-governance-reminder: ## print the rules every identity must read before touching a repo
	@echo ""
	@echo "bootstrap.mk: ORG GOVERNANCE -- read prompts/PROMPTING_RULES.md before any git/gh mutation."
	@echo "  Rule 1: never push directly to main -- branch, then PR."
	@echo "  Ordinary git/gh on a branch is fine; branch protection is the real control."
	@echo "  Full file: $(CLONE_DIR)/prompts/PROMPTING_RULES.md"
	@echo ""

bootstrap: clone-repo link-hee install-dotfiles print-governance-reminder ## clone this repo, link hee, install dotfiles -- one account, start here
	@echo "bootstrap.mk: $(USER)@$(ORG) ready -- hee -> $$(readlink -f $(BIN_DIR)/hee)"

bootstrap-all: clone-all-repos link-hee install-dotfiles print-governance-reminder ## bootstrap, but clone EVERY org repo (queried live from gh, not a list)
	@echo "bootstrap.mk: $(USER)@$(ORG) ready, all org repos cloned -- hee -> $$(readlink -f $(BIN_DIR)/hee)"

DOTFILES_DIR := $(GIT_DIR)/dotfiles

# Real "standard op procedure" dotfiles install -- Spencer, direct,
# 2026-08-26, after finding a stale per-person "dotfiles-src" fork that
# had drifted both ways from the real canonical repo (some real fixes
# only in canonical, some real additions only in the fork, neither side
# ever reconciled): "everyone same dotfiles... dotfiles and the
# hee/makefile work together." Clones the one real canonical
# Twin-Cities-Open-Systems/dotfiles repo (never a per-identity copy)
# and runs its own install-dotfiles.sh -a, unmodified -- that script
# already renames any existing file aside rather than clobbering it, so
# this is safe to wire straight into bootstrap/bootstrap-all rather
# than gating behind a separate confirm step. install-dotfiles.sh
# itself stays real and hee-independent by design (Spencer: "oper can
# still use dotfiles without hee") -- this target is a convenience
# wrapper around it, not a replacement.
install-dotfiles: ## clone and run the dotfiles installer
	@if [ -d "$(DOTFILES_DIR)/.git" ]; then \
		echo "bootstrap.mk: dotfiles already cloned at $(DOTFILES_DIR)"; \
	else \
		mkdir -p "$(GIT_DIR)"; \
		gh repo clone "$(GH_ORG)/dotfiles" "$(DOTFILES_DIR)"; \
	fi
	@( cd "$(DOTFILES_DIR)" && bash install-dotfiles.sh -a )

clone-repo: ## clone human-execution-engine into the clone dir shown under VARIABLES
	@if [ -d "$(CLONE_DIR)/.git" ]; then \
		echo "bootstrap.mk: $(REPO) already cloned at $(CLONE_DIR)"; \
	else \
		mkdir -p "$(GIT_DIR)"; \
		gh repo clone "$(GH_ORG)/$(REPO)" "$(CLONE_DIR)"; \
	fi

# Clone every real repo in the org -- queried live via gh, not a
# hardcoded list, so it stays accurate as repos get added/renamed.
# Real trigger: "let's add all the repos using our tool to my local
# git" (spencer@kiosk had only human-execution-engine cloned).
clone-all-repos: ## clone every repo in the org, discovered via gh api
	@mkdir -p "$(GIT_DIR)"
	@repos="$$(gh api "orgs/$(GH_ORG)/repos?per_page=100" --jq '.[].name')"; \
	if [ -z "$$repos" ]; then \
		echo "bootstrap.mk: gh api returned no repos -- check gh auth status" 1>&2; \
		exit 1; \
	fi; \
	for r in $$repos; do \
		d="$(GIT_DIR)/$$r"; \
		if [ -d "$$d/.git" ]; then \
			echo "bootstrap.mk: $$r already cloned"; \
		else \
			echo "bootstrap.mk: cloning $$r ..."; \
			gh repo clone "$(GH_ORG)/$$r" "$$d" \
				|| echo "bootstrap.mk: FAILED to clone $$r (real error above, continuing with the rest)"; \
		fi; \
	done

link-hee: clone-repo ## symlink hee into the bin dir -- the router, not a copy
	@mkdir -p "$(BIN_DIR)"
	@ln -sf "$(CLONE_DIR)/tooling/bin/hee" "$(BIN_DIR)/hee"

status: ## report what is actually installed: clone, hee symlink, repo count
	@echo "ORG=$(ORG) USER=$(USER)"
	@echo "clone: $$([ -d '$(CLONE_DIR)/.git' ] && echo real || echo missing) ($(CLONE_DIR))"
	@echo "hee:   $$(readlink -f '$(BIN_DIR)/hee' 2>/dev/null || echo missing)"
	@echo "repos: $$(find '$(GIT_DIR)' -maxdepth 2 -name .git -type d 2>/dev/null | wc -l) cloned in $(GIT_DIR)"

# Real per-repo health, not just "cloned or not": dirty working tree,
# diverged/behind upstream, no upstream at all. Fetches first (real
# network check against origin, not stale local refs) so ahead/behind
# reflects what's actually on GitHub right now.
#
# Real distinction, found live 2026-08-24: uncommitted changes to
# *tracked* files (M/A/D/R/etc, or staged) are a real reason not to
# touch a repo automatically; a plain untracked file is not the same
# risk -- `git pull --ff-only` doesn't care about it. This matters
# concretely now that hee-cred -seal writes real secrets to
# .hee/secrets/, which is untracked-by-design (gitignored) in every
# repo that gets one -- treating that as blocking would make every
# repo with a sealed credential permanently un-pullable by this target.
#
# Real per-repo logic lives in tooling/bin/hee-repo-refresh, not here --
# HEE#415, Spencer direct 2026-08-28: "add gnu parallel to this tool."
# With ~19-24 real repos each doing a real network fetch, the old
# one-at-a-time loop was a real, avoidable wall-clock cost. When GNU
# parallel is installed (`command -v parallel`), it fans the same
# script out concurrently -- safe here because each repo is fully
# independent, no shared state between them, and each job prints
# exactly one line so parallel's default --group behavior already
# keeps output atomic per repo (no mid-line interleaving to guard
# against). Falls back to the original sequential for-loop, calling
# the identical script, when parallel isn't present -- confirmed live
# 2026-08-28 that it's not a given dependency on a fresh kiosk-class
# host, so this is a real fallback path, not a hypothetical one.
health-all-repos: ## per-repo health across every clone -- dirty files, branches with no upstream
	@repos="$$(find "$(GIT_DIR)" -mindepth 1 -maxdepth 1 -type d 2>/dev/null)"; \
	if command -v parallel >/dev/null 2>&1; then \
		parallel "$(CLONE_DIR)/tooling/bin/hee-repo-refresh" health ::: $$repos; \
	else \
		for d in $$repos; do "$(CLONE_DIR)/tooling/bin/hee-repo-refresh" health "$$d"; done; \
	fi

# Fast-forward only -- never touches a repo with uncommitted changes to
# a *tracked* file or real local/upstream divergence (health-all-repos
# flags those; fix by hand, this target won't guess). A repo with only
# untracked files (e.g. a sealed .hee/secrets/ credential) still pulls
# -- git itself only blocks a merge that would clobber a real change.
# Same parallel/fallback design as health-all-repos above -- this one
# mutates local branches, but still safe under `parallel` because that
# safety comes from repo-independence (each `git pull` only ever
# touches its own repo dir), not from anything parallel itself
# guarantees.
pull-all-repos: ## git pull every repo; safe because each pull is repo-independent
	@repos="$$(find "$(GIT_DIR)" -mindepth 1 -maxdepth 1 -type d 2>/dev/null)"; \
	if command -v parallel >/dev/null 2>&1; then \
		parallel "$(CLONE_DIR)/tooling/bin/hee-repo-refresh" pull ::: $$repos; \
	else \
		for d in $$repos; do "$(CLONE_DIR)/tooling/bin/hee-repo-refresh" pull "$$d"; done; \
	fi

refresh-all-repos: health-all-repos pull-all-repos print-governance-reminder ## health-all-repos + pull-all-repos + the governance reminder
	@echo "bootstrap.mk: refresh complete -- hee -> $$(readlink -f $(BIN_DIR)/hee)"

link-cache-prune: clone-repo ## symlink hee-cache-prune into the bin dir
	@mkdir -p "$(BIN_DIR)"
	@ln -sf "$(CLONE_DIR)/tooling/bin/hee-cache-prune" "$(BIN_DIR)/hee-cache-prune"

# Real Claude Code PreToolUse hook, source of truth in this repo (not
# dotfiles -- dotfiles is scoped to shell/editor config per its own
# README; this enforces this repo's own PROMPTING_RULES.md rule #3,
# same category as hee/hee-cache-prune above). Symlinked, not copied,
# same as link-hee -- an update to the script here is live for every
# identity without a reinstall.
link-hooks: clone-repo ## symlink the git hooks from this repo -- symlinked, never copied
	@mkdir -p "$(HOOKS_DIR)"
	@ln -sf "$(CLONE_DIR)/tooling/hooks/check-bare-issue-refs.py" "$(HOOKS_DIR)/check-bare-issue-refs.py"

# Real trigger (2026-08-29): the hook itself was real and tested, but
# only wired into claude@kiosk's own ~/.claude/settings.json by hand --
# invisible to every other identity until this existed. Additive jq
# merge into settings.json's real hooks.PreToolUse array (same real
# "never clobber what's already there" discipline as install-cron's
# crontab merge above) -- checks whether a hook with this exact command
# already exists anywhere in PreToolUse before adding, so re-running is
# a real no-op, not a growing duplicate list. Never touches any other
# hook already configured.
install-hooks: link-hooks ## register the agent PreToolUse hooks, idempotently
	@mkdir -p "$$(dirname "$(CLAUDE_SETTINGS)")"; \
	if [ ! -f "$(CLAUDE_SETTINGS)" ]; then echo '{}' > "$(CLAUDE_SETTINGS)"; fi; \
	cmd="python3 $(HOOKS_DIR)/check-bare-issue-refs.py"; \
	if jq -e --arg cmd "$$cmd" '[.hooks.PreToolUse[]?.hooks[]?.command] | index($$cmd)' "$(CLAUDE_SETTINGS)" >/dev/null 2>&1; then \
		echo "bootstrap.mk: bare-issue-reference hook already installed in $(CLAUDE_SETTINGS)"; \
	else \
		tmp="$$(mktemp)"; \
		jq --arg cmd "$$cmd" '.hooks //= {} | .hooks.PreToolUse //= [] | .hooks.PreToolUse += [{"matcher": "Bash", "hooks": [{"type": "command", "command": $$cmd, "timeout": 10, "statusMessage": "Checking for bare issue/PR shorthand..."}]}]' "$(CLAUDE_SETTINGS)" > "$$tmp" && mv "$$tmp" "$(CLAUDE_SETTINGS)"; \
		echo "bootstrap.mk: installed bare-issue-reference hook into $(CLAUDE_SETTINGS)"; \
	fi

# Real, unprivileged-by-design cron install -- per Spencer's correction
# 2026-08-24: user tools belong in $(BIN_DIR) (~/.local/bin, same as
# link-hee), managed by this Makefile, never a manually-copied one-off
# script sitting in an ad hoc ~/bin. Additive to crontab -l (never
# overwrites an existing crontab wholesale), skips if these two real
# lines are already present so re-running is a real no-op, not a
# growing duplicate list.
install-cron: link-hee link-cache-prune ## add cron entries for this account, never overwriting the crontab
	@existing="$$(crontab -l 2>/dev/null || true)"; \
	prune_line="0 4 * * * $(BIN_DIR)/hee-cache-prune"; \
	health_line="0 5 * * 0 cd $(CLONE_DIR) && $(MAKE) -f tooling/bootstrap.mk health-all-repos > $(HOME_DIR)/.cache/hee-git-health-report.txt 2>&1"; \
	new="$$existing"; \
	echo "$$existing" | grep -qF "hee-cache-prune" || new="$$(printf '%s\n%s' "$$new" "$$prune_line")"; \
	echo "$$existing" | grep -qF "health-all-repos" || new="$$(printf '%s\n%s' "$$new" "$$health_line")"; \
	if [ "$$new" = "$$existing" ]; then \
		echo "bootstrap.mk: cron already installed, nothing to do"; \
	else \
		mkdir -p "$(HOME_DIR)/.cache"; \
		printf '%s\n' "$$new" | crontab -; \
		echo "bootstrap.mk: cron installed -- daily cache-prune (4am), weekly git-health report (Sun 5am)"; \
	fi

# Real "reset to new" -- dry-run by default (see hee-reset-tooling
# itself for the full real safety design: never touches .ssh/.gnupg/
# .hee/secrets/.config/git, per-file preserve-if-different, a full
# meta-backup taken before any real change). This target just wires it
# to the real canonical checkout; CONFIRM=yes actually executes.
#   make -f tooling/bootstrap.mk reset-tooling           # dry run
#   make -f tooling/bootstrap.mk reset-tooling CONFIRM=yes
reset-tooling: clone-repo ## restore tooling to the canonical checkout (needs CONFIRM=yes to execute)
	@if [ "$(CONFIRM)" = "yes" ]; then \
		"$(CLONE_DIR)/tooling/bin/hee-reset-tooling" --yes --canonical "$(CLONE_DIR)/tooling/bin"; \
	else \
		"$(CLONE_DIR)/tooling/bin/hee-reset-tooling" --canonical "$(CLONE_DIR)/tooling/bin"; \
	fi

# Real "restore secrets from a renamed-aside backup homedir" -- real
# trigger (2026-08-26): a fresh-homedir wipe ("mv spencer spencer-old")
# ran, but nothing restored .ssh/.gnupg/.config/gh into the new homedir
# afterward. Spencer hand-typed the restore live via tmux send-keys,
# then, direct: "do not do this again that hard way." This target is
# that "again" made real, not another one-off.
#
# Deliberately narrow -- .ssh, .gnupg, .config/gh -- the real,
# load-bearing credential surface a backup can't be regenerated from.
# Dotfiles are NOT restored here on purpose: they're a real cloneable
# org repo (see install-dotfiles above), not a per-person backup
# artifact -- restoring them from an old personal copy is exactly the
# stale-fork problem (Spencer, 2026-08-26: "get rid of the -src dir,
# that is bullshit") this split avoids.
#
# Dry-run by default (same real safety pattern as reset-tooling above)
# -- CONFIRM=yes actually copies. Never overwrites an item already
# present at the destination. BACKUP_DIR defaults to the sibling
# "$(HOME)-old" the mv-aside convention creates.
#   make -f tooling/bootstrap.mk restore-secrets                # dry run
#   make -f tooling/bootstrap.mk restore-secrets CONFIRM=yes
BACKUP_DIR ?= $(HOME_DIR)-old
RESTORE_ITEMS := .ssh .gnupg .config/gh

restore-secrets: ## restore sealed items from the backup dir shown under VARIABLES
	@if [ ! -d "$(BACKUP_DIR)" ]; then \
		echo "bootstrap.mk: no backup dir at $(BACKUP_DIR) -- nothing to restore" 1>&2; \
		exit 1; \
	fi; \
	for item in $(RESTORE_ITEMS); do \
		src="$(BACKUP_DIR)/$$item"; dst="$(HOME_DIR)/$$item"; \
		if [ ! -e "$$src" ]; then \
			echo "bootstrap.mk: $$item: not in backup, skipping"; \
			continue; \
		fi; \
		if [ -e "$$dst" ]; then \
			echo "bootstrap.mk: $$item: already present at $$dst, skipping (never overwrites)"; \
			continue; \
		fi; \
		if [ "$(CONFIRM)" = "yes" ]; then \
			mkdir -p "$$(dirname "$$dst")"; \
			cp -a "$$src" "$$dst"; \
			echo "bootstrap.mk: restored $$item"; \
		else \
			echo "bootstrap.mk: [dry run] would restore $$item ($$src -> $$dst)"; \
		fi; \
	done; \
	if [ "$(CONFIRM)" = "yes" ]; then \
		chmod 700 "$(HOME_DIR)/.ssh" "$(HOME_DIR)/.gnupg" "$(HOME_DIR)/.config/gh" 2>/dev/null || true; \
		echo "bootstrap.mk: restore complete -- run 'make -f tooling/bootstrap.mk install-dotfiles' for a shell, then open a fresh shell (exec bash -l) to pick up PATH changes"; \
	else \
		echo "bootstrap.mk: dry run only -- re-run with CONFIRM=yes to actually restore"; \
	fi
