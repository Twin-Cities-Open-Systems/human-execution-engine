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

.PHONY: bootstrap bootstrap-all clone-repo clone-all-repos link-hee status

bootstrap: clone-repo link-hee
	@echo "bootstrap.mk: $(USER)@$(ORG) ready -- hee -> $$(readlink -f $(BIN_DIR)/hee)"

bootstrap-all: clone-all-repos link-hee
	@echo "bootstrap.mk: $(USER)@$(ORG) ready, all org repos cloned -- hee -> $$(readlink -f $(BIN_DIR)/hee)"

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
