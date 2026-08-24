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
REPO := human-execution-engine
GIT_URL := https://github.com/Twin-Cities-Open-Systems/$(REPO)
HOME_DIR := $(HOME)
CLONE_DIR := $(HOME_DIR)/git/$(REPO)
BIN_DIR := $(HOME_DIR)/.local/bin

.PHONY: bootstrap clone-repo link-hee status

bootstrap: clone-repo link-hee
	@echo "bootstrap.mk: $(USER)@$(ORG) ready -- hee -> $$(readlink -f $(BIN_DIR)/hee)"

clone-repo:
	@if [ -d "$(CLONE_DIR)/.git" ]; then \
		echo "bootstrap.mk: $(REPO) already cloned at $(CLONE_DIR)"; \
	else \
		mkdir -p "$(HOME_DIR)/git"; \
		git clone "$(GIT_URL)" "$(CLONE_DIR)"; \
	fi

link-hee: clone-repo
	@mkdir -p "$(BIN_DIR)"
	@ln -sf "$(CLONE_DIR)/tooling/bin/hee" "$(BIN_DIR)/hee"

status:
	@echo "ORG=$(ORG) USER=$(USER)"
	@echo "clone: $$([ -d '$(CLONE_DIR)/.git' ] && echo real || echo missing) ($(CLONE_DIR))"
	@echo "hee:   $$(readlink -f '$(BIN_DIR)/hee' 2>/dev/null || echo missing)"
