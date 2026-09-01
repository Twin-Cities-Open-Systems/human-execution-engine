# HEE Vendor Hardening Specification

**File:** docs/HEE_VENDOR_HARDENING_SPEC.md
**Status:** Proposed → Required
**Scope:** Tooling (derivative)
**Authority:** human-execution-engine
**Doctrine Rule:** doctrine is normative; tooling is derivative

---

## 1. Problem Statement

`hee-vendor` is currently **operationally effective but audit-unsafe**.

### Root Failures

1. **No read-only mode**
   Audits mutate state (branches, commits, PRs), violating basic operational safety.

2. **Formatter interference**
   Consumer-side hooks (e.g., Prettier) rewrite vendored files post-commit, breaking determinism.

3. **Non-idempotent behavior**
   Re-running vendoring can produce diffs or branches even when upstream is unchanged.

These failures prevent:

* Safe audits
* Deterministic CI validation
* Confident scaling to additional consumer repositories

---

## 2. Design Goals (Non-Negotiable)

1. **Audit safety** – audits MUST be non-mutating
2. **Determinism** – unchanged upstream MUST produce zero diffs
3. **Formatter resilience** – downstream formatters MUST NOT break vendoring
4. **Doctrine preservation** – canonical HEE is the single source of truth
5. **Operational clarity** – failures MUST be explicit and actionable

---

## 3. CLI Contract

### 3.1 Required Flags

#### `--check`

**Purpose:** Read-only audit

**Behavior:**

* MUST NOT:

  * create branches
  * modify files
  * commit
  * push
  * open PRs
* MUST:

  * compute what *would* change
  * exit non-zero if drift exists

**Exit Codes:**

* `0` → compliant, no diffs
* `2` → drift detected
* `>2` → tooling error

---

#### `--plan` (recommended)

**Purpose:** Dry-run execution plan

**Behavior:**

* Same non-mutating guarantees as `--check`
* Prints:

  * files that would change
  * branch name
  * commit message
  * PR title and body

---

#### `--no-push`

**Purpose:** Local mutation only

**Behavior:**

* Allows branch creation and commits
* Prohibits:

  * pushing
  * PR creation

---

#### `--auto-amend`

**Purpose:** Formatter convergence

**Behavior:**

* After vendoring commit:

  * detect post-hook rewrites
  * stage rewritten files
  * amend commit
  * repeat until clean (bounded)

**Expectation:** This becomes the default once proven stable.

---

## 4. Operational Modes

| Mode        | Mutates Files | Commits | Pushes | PRs |
| ----------- | ------------- | ------- | ------ | --- |
| `--check`   | No            | No      | No     | No  |
| `--plan`    | No            | No      | No     | No  |
| Default     | Yes           | Yes     | Yes    | Yes |
| `--no-push` | Yes           | Yes     | No     | No  |

---

## 5. Preflight Safety Checks (MUST)

Before any mutating operation:

* Repository is a valid git repo
* No in-progress merge or rebase
* Working tree is clean unless `--allow-dirty` is set
* Base branch exists (default: `main`)
* Remote configured when pushing is enabled
* Vendor branch collisions handled explicitly

Failure MUST abort early with a clear error message.

---

## 6. Deterministic Vendoring

### 6.1 Provenance Marker (Required)

Each consumer repo MUST contain:

```sh
docs/hee/VENDORED_FROM.yml <!-- hee-check:refs-ok  created in the consumer repo, never present here -->
```

**Minimum contents:**

* canonical repo identifier
* upstream commit SHA
* vendoring tool version
* vendoring timestamp

### 6.2 Early Exit Rule

If:

* upstream SHA matches canonical
* rendered vendored tree matches working tree

→ `hee-vendor` MUST exit successfully without changes.

---

## 7. Formatter Resilience (Auto-Amend Loop)

### Required Behavior

After applying vendored updates:

1. Stage vendored paths
2. Create commit (or amend if branch exists)
3. Detect post-commit changes via `git status --porcelain`
4. If dirty:

   * stage rewritten files
   * `git commit --amend --no-edit`
5. Repeat up to two passes
6. Assert clean working tree before push or PR creation

Failure to converge MUST error loudly and abort.

---

## 8. Read-Only Audit Implementation Model

Canonical implementation:

* Render canonical HEE content into a temporary directory
* Diff against consumer vendored paths using:

```sh
git diff --no-index
```

* Never modify tracked files

This guarantees:

* zero mutation
* accurate drift detection
* CI-safe audits

---

## 9. Upstream Format Normalization (Recommended)

To reduce downstream diffs:

* Normalize canonical HEE YAML formatting to common formatter defaults
* Scope normalization strictly to vendored content

This is optional but strongly recommended for scale.

---

## 10. Acceptance Criteria (Release Gate)

`hee-vendor` is considered **hardened** only when:

1. `--check` produces no mutations under any condition
2. Re-running vendoring with unchanged upstream produces zero diffs
3. Formatter-interfering repos converge in one run
4. Dirty repos fail fast unless explicitly overridden
5. Audit workflows never create branches or commits

---

## 11. Doctrine Alignment

This hardening:

* Preserves doctrine > tooling precedence
* Makes audits safe and automatable
* Enables confident expansion to additional consumer repos
* Removes humans from the formatter-repair critical path

---

## 12. Canonical Git Workflow (One-Shot)

The following sequence is the **approved, single-shot workflow** to land this specification into the canonical repository.

```sh
# from ~/git/human-execution-engine

git status
# ensure clean working tree

git add docs/HEE_VENDOR_HARDENING_SPEC.md

git commit -m "docs(hee-vendor): add hardening specification for audit safety and determinism"

git push -u origin HEAD

# open PR (gh CLI)
gh pr create \
  --title "HEE vendor hardening specification" \
  --body "Adds the canonical hardening spec for hee-vendor, defining audit-safe modes, formatter resilience, and deterministic vendoring behavior." \
  --base main

# after review approval
gh pr merge --squash --delete-branch
```

This workflow is normative for introducing this specification.

---

**End of specification**
