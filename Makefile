# HEE Makefile (small, opt-in, packages)
# Defaults: repo-local installs for determinism + easy undo.

REPO_ROOT := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
HEE_PREFIX ?= $(REPO_ROOT)/.hee
BINDIR     ?= $(HEE_PREFIX)/bin

MAN1DIR    ?= $(HOME)/.local/share/man/man1
COMPDIR    ?= $(HOME)/.local/share/bash-completion/completions

TOOLS := hee hee-print hee-fileident hee-pathcheck hee-http404

.PHONY: help
help:
	@echo "hee make"
	@echo
	@echo "USAGE:"
	@echo "  make <target> [HEE_PREFIX=...]"
	@echo
	@echo "DEFAULTS:"
	@echo "  HEE_PREFIX=$(HEE_PREFIX)"
	@echo
	@echo "TARGETS:"
	@echo "  install-cli            install library/sh tools into $${HEE_PREFIX}/bin"
	@echo "  uninstall-cli          remove installed tools from $${HEE_PREFIX}/bin"
	@echo "  install-man            install hee(1) manpage into $(MAN1DIR)"
	@echo "  uninstall-man          uninstall hee(1) manpage"
	@echo "  install-bash-completion install hee completion (candidates + meanings from --help) into $(COMPDIR)/hee"
	@echo "  uninstall-bash-completion uninstall bash completion"
	@echo "  doctor                 show env + PATH + unfuck hints"
	@echo "  test-drive             create test-drive branch + repo-local install + generate site (no serve)"
	@echo "  test-drive-serve        serve UIBOSS_DOCROOT (blocking; use in its own terminal)"

.PHONY: install-cli
install-cli:
	@mkdir -p "$(BINDIR)"
	@for t in $(TOOLS); do \
	  cp -f "$(REPO_ROOT)/library/sh/$$t" "$(BINDIR)/$$t"; \
	  chmod +x "$(BINDIR)/$$t"; \
	  echo "🟢 installed: $(BINDIR)/$$t"; \
	done
	@echo "🟦 run (repo-local): $(BINDIR)/hee --help"

.PHONY: uninstall-cli
uninstall-cli:
	@for t in $(TOOLS); do \
	  rm -f "$(BINDIR)/$$t"; \
	  echo "🟦 removed (if present): $(BINDIR)/$$t"; \
	done

.PHONY: install-man
install-man:
	@mkdir -p "$(MAN1DIR)"
	@for m in "$(REPO_ROOT)"/man/*.1; do \
	  gzip -c "$$m" >"$(MAN1DIR)/$$(basename $$m).gz"; \
	  echo "🟢 installed: $(MAN1DIR)/$$(basename $$m).gz"; \
	done
	@echo "🟦 test: MANPATH=$(MAN1DIR:%/man1=%/man):\$$MANPATH man hee"

.PHONY: uninstall-man
uninstall-man:
	@for m in "$(REPO_ROOT)"/man/*.1; do \
	  rm -f "$(MAN1DIR)/$$(basename $$m).gz"; \
	done
	@echo "🟦 removed (if present): all $(MAN1DIR)/*.gz from man/"

.PHONY: install-bash-completion
install-bash-completion:
	@# generated from every tool's own --help; dotfiles' .bashrc loads $(COMPDIR)/hee
	@"$(REPO_ROOT)/tooling/bin/hee-completion" install

.PHONY: uninstall-bash-completion
uninstall-bash-completion:
	@rm -f "$(COMPDIR)/hee"
	@echo "🟦 removed (if present): $(COMPDIR)/hee"

.PHONY: doctor
doctor:
	@echo "🔵 doctor"
	@echo "🟦 repo_root=$(REPO_ROOT)"
	@echo "🟦 HEE_PREFIX=$(HEE_PREFIX)"
	@echo "🟦 BINDIR=$(BINDIR)"
	@echo "🟦 command -v hee:"
	@command -v hee 2>/dev/null || echo "🟠 hee not on PATH"
	@echo "🟦 bash type -a hee (if bash available):"
	@bash -lc 'type -a hee 2>/dev/null || echo "🟦 (none)"' || true
	@echo "🟦 hash-clear (interactive shell): hash -d hee || hash -r"
	@echo "🟦 gh git-credential helper (avoids the HTTPS username/password"
	@echo "   footgun -- GitHub doesn't accept password auth for git ops):"
	@if git config --get-all credential.helper 2>/dev/null | grep -q "gh auth git-credential"; then \
	  echo "🟢 configured"; \
	else \
	  echo "🟠 not configured -- run: gh auth setup-git"; \
	fi
	@echo "🟦 git unfuck quick hints:"
	@echo "  git status -sb"
	@echo "  git reflog"
	@echo "  git branch --show-current"
	@echo "  if you need a rescue branch first: git checkout -b rescue/$$(date +%Y%m%d-%H%M%S)"
	@$(MAKE) --no-print-directory doctor-env

# Real identity-env check, same real fields tools/agent-signature.sh
# reads (contracts/agent-instance-signature-v1.contract.yaml) -- not a
# separately-invented env scheme. Works the same for a human operator
# shell and an agent shell: CLAUDE_CODE_SESSION_ID being unset just
# means "this is a human," reported plainly, not an error.
.PHONY: doctor-env
doctor-env:
	@echo "🔵 doctor-env (real identity fields, human or agent)"
	@if [ -n "$$CLAUDE_CODE_SESSION_ID" ]; then \
	  echo "🟢 identity: agent session (CLAUDE_CODE_SESSION_ID set)"; \
	else \
	  echo "🟦 identity: human operator shell (CLAUDE_CODE_SESSION_ID unset)"; \
	fi
	@echo "🟦 CLAUDE_CODE_SESSION_ID=$${CLAUDE_CODE_SESSION_ID:-<unset>}"
	@echo "🟦 CLAUDE_PID=$${CLAUDE_PID:-<unset, would default to \$$\$$>}"
	@if [ -n "$$TMUX" ]; then \
	  echo "🟢 tmux: attached (TMUX_SESSION=$${TMUX_SESSION:-unknown} TMUX_PANE=$${TMUX_PANE:-unknown})"; \
	else \
	  echo "🟦 tmux: not attached"; \
	fi
	@echo "🟦 CLAUDE_CODE_MESSAGING_SOCKET=$${CLAUDE_CODE_MESSAGING_SOCKET:-<unset>}"
	@printf "🟦 gh auth: "; \
	  gh auth status >/dev/null 2>&1 && gh auth status 2>&1 | grep -oP 'account \K\S+' | head -1 || echo "🟠 not logged in (gh auth login)"
	@printf "🟦 gpg default signing key: "; \
	  gpg --list-secret-keys --keyid-format long 2>/dev/null | grep -q '^sec' && echo "present" || echo "🟠 none found (gpg --full-generate-key or import one)"
	@echo "🟦 real signature block this identity would produce:"
	@bash "$(REPO_ROOT)/tools/agent-signature.sh" 2>/dev/null | sed 's/^/  /' || echo "  🟠 tools/agent-signature.sh failed"

.PHONY: test-drive
test-drive:
	@echo "🔵 test-drive (demo UX, not infra)"
	@test -z "$$(git status --porcelain)" || { echo "🔴 dirty tree; stop"; exit 2; }
	@BR="test-drive/$$(date +%Y%m%d-%H%M%S)"; \
	  git checkout -b "$$BR"; \
	  echo "🟢 branch: $$BR"; \
	  $(MAKE) install-cli HEE_PREFIX="$(REPO_ROOT)/.hee"; \
	  $(MAKE) install-man; \
	  $(MAKE) install-bash-completion; \
	  echo "🟦 run: $(REPO_ROOT)/.hee/bin/hee ls"; \
	  "$(REPO_ROOT)/.hee/bin/hee" ls; \
	  if command -v uiboss >/dev/null 2>&1; then \
	    echo "🟢 uiboss: generate site"; \
	    uiboss run ui.site.generate || true; \
	    echo "🟦 url: http://127.0.0.1:7777/"; \
	    echo "🟦 start server (separate terminal): make test-drive-serve"; \
	  else \
	    echo "🟠 uiboss not on PATH (expected if not installed)"; \
	  fi; \
	  echo "🟦 undo demo artifacts: rm -rf $(REPO_ROOT)/.hee"

.PHONY: test-drive-serve
test-drive-serve:
	@echo "🔵 serve (blocking)"
	@DOCROOT="$${UIBOSS_DOCROOT:-$${UIBOSS_SITE_ROOT:-$(HOME)/.hee/uiboss/site}}"; \
	  echo "🟦 DOCROOT=$$DOCROOT"; \
	  "$(REPO_ROOT)/.hee/bin/hee" serve --bind 127.0.0.1 --port 7777
