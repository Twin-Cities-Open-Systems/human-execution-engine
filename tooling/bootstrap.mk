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

.PHONY: bootstrap bootstrap-all clone-repo clone-all-repos link-hee status \
        health-all-repos pull-all-repos refresh-all-repos print-governance-reminder \
        link-cache-prune install-cron reset-tooling restore-secrets install-dotfiles

# Real trigger (2026-08-28): an agent session ran raw git commit/merge
# repeatedly across three repos before ever reading PROMPTING_RULES.md --
# the rules were real and canonical the whole time, just never surfaced
# at the one moment (env bootstrap/refresh) every identity actually
# passes through. Spencer, direct: "must not be missed again... you
# guys act like idiots otherwise." Printed, not just linked, so it
# can't be silently scrolled past the way a bare path can.
print-governance-reminder:
	@echo ""
	@echo "bootstrap.mk: ORG GOVERNANCE -- read prompts/PROMPTING_RULES.md before any git/gh mutation."
	@echo "  Rule #1: every git/gh mutation goes through scripts/hee_git_ops.sh <op> --act --reason \"...\""
	@echo "  with HEE_TOOL_MODE=ACT set. Raw git commit/push/merge by an agent is not allowed."
	@echo "  Full file: $(CLONE_DIR)/prompts/PROMPTING_RULES.md"
	@echo ""

bootstrap: clone-repo link-hee install-dotfiles print-governance-reminder
	@echo "bootstrap.mk: $(USER)@$(ORG) ready -- hee -> $$(readlink -f $(BIN_DIR)/hee)"

bootstrap-all: clone-all-repos link-hee install-dotfiles print-governance-reminder
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
install-dotfiles:
	@if [ -d "$(DOTFILES_DIR)/.git" ]; then \
		echo "bootstrap.mk: dotfiles already cloned at $(DOTFILES_DIR)"; \
	else \
		mkdir -p "$(GIT_DIR)"; \
		gh repo clone "$(GH_ORG)/dotfiles" "$(DOTFILES_DIR)"; \
	fi
	@( cd "$(DOTFILES_DIR)" && bash install-dotfiles.sh -a )

clone-repo:
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
clone-all-repos:
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

link-hee: clone-repo
	@mkdir -p "$(BIN_DIR)"
	@ln -sf "$(CLONE_DIR)/tooling/bin/hee" "$(BIN_DIR)/hee"

status:
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
health-all-repos:
	@for d in $$(find "$(GIT_DIR)" -mindepth 1 -maxdepth 1 -type d 2>/dev/null); do \
		r=$$(basename "$$d"); \
		[ -d "$$d/.git" ] || continue; \
		git -C "$$d" fetch --quiet 2>/dev/null; \
		branch=$$(git -C "$$d" branch --show-current 2>/dev/null); \
		status=$$(git -C "$$d" status --porcelain 2>/dev/null); \
		tracked_dirty=$$(echo "$$status" | grep -v '^??' | grep -c . || true); \
		untracked=$$(echo "$$status" | grep -c '^??' || true); \
		upstream=$$(git -C "$$d" rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null); \
		if [ -n "$$upstream" ]; then \
			set -- $$(git -C "$$d" rev-list --left-right --count "HEAD...$$upstream" 2>/dev/null); \
			ahead=$${1:-0}; behind=$${2:-0}; \
		else \
			ahead=0; behind=0; \
		fi; \
		untracked_note=""; \
		[ "$$untracked" != "0" ] && untracked_note=" ($$untracked untracked, fine to pull through)"; \
		if [ "$$tracked_dirty" != "0" ] && [ "$$behind" != "0" ]; then \
			echo "🔴 $$r: dirty ($$tracked_dirty uncommitted) AND $$behind behind $$branch -- resolve by hand first"; \
		elif [ "$$tracked_dirty" != "0" ]; then \
			echo "🟠 $$r: dirty ($$tracked_dirty uncommitted) on $$branch"; \
		elif [ "$$ahead" != "0" ] && [ "$$behind" != "0" ]; then \
			echo "🟠 $$r: diverged ($$ahead ahead / $$behind behind $$branch)"; \
		elif [ -z "$$upstream" ]; then \
			echo "🟡 $$r: no upstream tracking branch ($$branch)$$untracked_note"; \
		elif [ "$$behind" != "0" ]; then \
			echo "🟡 $$r: $$behind behind $$branch -- pull-all-repos will fast-forward$$untracked_note"; \
		else \
			echo "🟢 $$r: clean, up to date ($$branch)$$untracked_note"; \
		fi; \
	done

# Fast-forward only -- never touches a repo with uncommitted changes to
# a *tracked* file or real local/upstream divergence (health-all-repos
# flags those; fix by hand, this target won't guess). A repo with only
# untracked files (e.g. a sealed .hee/secrets/ credential) still pulls
# -- git itself only blocks a merge that would clobber a real change.
pull-all-repos:
	@for d in $$(find "$(GIT_DIR)" -mindepth 1 -maxdepth 1 -type d 2>/dev/null); do \
		r=$$(basename "$$d"); \
		[ -d "$$d/.git" ] || continue; \
		tracked_dirty=$$(git -C "$$d" status --porcelain 2>/dev/null | grep -v '^??' | grep -c . || true); \
		if [ "$$tracked_dirty" != "0" ]; then \
			echo "🟠 $$r: skipped -- $$tracked_dirty uncommitted change(s) to tracked files, not touching"; \
			continue; \
		fi; \
		out=$$(git -C "$$d" pull --ff-only 2>&1); \
		if [ $$? -eq 0 ]; then \
			echo "🟢 $$r: $$(echo "$$out" | tail -1)"; \
		else \
			echo "🔴 $$r: pull failed -- $$(echo "$$out" | tail -1)"; \
		fi; \
	done

refresh-all-repos: health-all-repos pull-all-repos print-governance-reminder
	@echo "bootstrap.mk: refresh complete -- hee -> $$(readlink -f $(BIN_DIR)/hee)"

link-cache-prune: clone-repo
	@mkdir -p "$(BIN_DIR)"
	@ln -sf "$(CLONE_DIR)/tooling/bin/hee-cache-prune" "$(BIN_DIR)/hee-cache-prune"

# Real, unprivileged-by-design cron install -- per Spencer's correction
# 2026-08-24: user tools belong in $(BIN_DIR) (~/.local/bin, same as
# link-hee), managed by this Makefile, never a manually-copied one-off
# script sitting in an ad hoc ~/bin. Additive to crontab -l (never
# overwrites an existing crontab wholesale), skips if these two real
# lines are already present so re-running is a real no-op, not a
# growing duplicate list.
install-cron: link-hee link-cache-prune
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
reset-tooling: clone-repo
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

restore-secrets:
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
