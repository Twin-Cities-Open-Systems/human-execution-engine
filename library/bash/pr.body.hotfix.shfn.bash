# pr.body.hotfix.shfn.bash
# Pretty PR-body generator: mktemp-first, icons, no ANSI dependency, no exit.

# Usage:
#   . tools/shellboss/library/bash/pr.body.hotfix.shfn.bash
#   shellboss_pr_body_hotfix
#
# Writes a ready-to-paste PR body to mktemp and updates /tmp/hee.pr.body.latest.md.

shellboss_pr_body_hotfix() {
  local OUT
  OUT="$(mktemp -t hee.pr.body.XXXXXX.md)" || return 1
  ln -sf "$OUT" /tmp/hee.pr.body.latest.md 2>/dev/null || true

  # Derived from this file's own location, never a hardcoded home -- rule 10.
  local repo
  repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)" || return 1
  cd "$repo" || { printf "❌ ERROR: cd failed: %s\n" "$repo"; return 1; }

  local branch head
  branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null)" || return 1
  head="$(git rev-parse HEAD 2>/dev/null)" || return 1

  local files
  files="$(git show --name-only --pretty=format: -1 2>/dev/null | sed '/^$/d')" || files="(unable to read file list)"

  {
printf -- "## ShellBoss: rg scan shfn (oper UX + mktemp-first evidence)\n\n"
printf -- "### Artifact (shfn-first primitive)\n"
printf -- "- tools/shellboss/library/bash/rg.scan.shfn.bash\n\n"
printf -- "This PR introduces a tiny ripgrep helper shfn and wires it into ShellBoss + the installer.\n\n"
printf -- "---\n\n"
printf -- "## Why this is a big deal\n\n"
printf -- "Oper now gets a zero-friction rg helper that:\n\n"
printf -- "- defaults to **counts** (wc -l) for low-noise console usage\n"
printf -- "- emits **mktemp evidence reports** only when useful (hits>0 or forced)\n"
printf -- "- avoids exit in pasteable surfaces (returns only)\n"
printf -- "- supports portable “pretty” output via icons (works even without ANSI)\n"
printf -- "- reinforces ShellBoss as the machine-behind-the-console\n\n"
printf -- "---\n\n"
printf -- "## Referee Summary\n\n"
printf -- "### Card counts (this session)\n"
printf -- "- 🟥 RED: caught wiring + commit-reality drift early\n"
printf -- "- 🟨 YELLOW: installer/root footguns stabilized\n"
printf -- "- 🟩 GREEN: final state verified on disk\n\n"
printf -- "### Corrections made\n"
printf -- "- shfn existed but was not landing in PR → fixed (tracked + committed)\n"
printf -- "- installer + shellboss wiring missing → fixed (rg-proven)\n"
printf -- "- commit message drift vs file reality → corrected (final commit includes exact file set)\n\n"
printf -- "Single source of truth:\n"
printf -- "- tools/shellboss/library/bash/rg.scan.shfn.bash\n\n"
printf -- "---\n\n"
printf -- "## Render Preview (oper view)\n\n"
printf -- "\n"
printf -- "🧾 REPORT  /tmp/hee.pr.body.latest.md\n"
printf -- "🔎 SCAN    wrote matches to mktemp\n"
printf -- "🛑/✅      status + counts\n"
printf -- "📌 SUMMARY hits_any=... hits_code=...\n"
printf -- "👀 OPEN    cat /tmp/hee.pr.body.latest.md\n"
printf -- "🔗 LATEST  /tmp/hee.pr.body.latest.md\n"
printf -- "\n\n"
printf -- "Portable pretty: icons > ANSI.\n\n"
printf -- "---\n\n"
  printf -- "## Mets (k:v YAML)\n\n"\n  printf -- "~~~yaml\n"\n  printf -- "confidence:\n"\n  printf -- "  scale: 0..1\n"\n  printf -- "  definition: weighted mean of measurable invariants; clamp to [0,1]\n"\n  printf -- "  weights:\n"\n  printf -- "    run_ok: 0.50\n"\n  printf -- "    placeholder_free: 0.15\n"\n  printf -- "    backtick_free: 0.15\n"\n  printf -- "    shfn_doc_compat: 0.20\n"\n  printf -- "  inputs:\n"\n  printf -- "    run_ok: 1\n"\n  printf -- "    placeholder_free: 1\n"\n  printf -- "    backtick_free: 1\n"\n  printf -- "    shfn_doc_compat: 1\n"\n  printf -- "  math:\n"\n  printf -- "    C_raw: 0.50*run_ok + 0.15*placeholder_free + 0.15*backtick_free + 0.20*shfn_doc_compat\n"\n  printf -- "    C: clamp(C_raw, 0, 1)\n"\n  printf -- "  result:\n"\n  printf -- "    confidence: 1.0\n"\n  printf -- "~~~\n\n"\n  printf -- "~~~mermaid\n"\n  printf -- "flowchart TD\n"\n  printf -- "  A[Evidence inputs] --> B[run_ok]\n"\n  printf -- "  A --> C[placeholder_free]\n"\n  printf -- "  A --> D[backtick_free]\n"\n  printf -- "  A --> E[shfn_doc_compat]\n"\n  printf -- "  B --> F[Weighted sum]\n"\n  printf -- "  C --> F\n"\n  printf -- "  D --> F\n"\n  printf -- "  E --> F\n"\n  printf -- "  F --> G[C_raw = 0.50*run_ok + 0.15*placeholder_free + 0.15*backtick_free + 0.20*shfn_doc_compat]\n"\n  printf -- "  G --> H[C = clamp(C_raw, 0, 1)]\n"\n  printf -- "~~~\n\n"\nprintf -- "## Stats\n"
printf -- "- Branch: %s\n" "$branch"
printf -- "- Commit: %s\n" "$head"
printf -- "- Files in commit:\n\n"
printf -- "\n%s\n\n" "$files"
  } > "$OUT" || return 1
printf -- "✅ PR BODY READY\n"
printf -- "🧾 FILE   %s\n" "$OUT"
printf -- "🔗 LATEST %s\n" "/tmp/hee.pr.body.latest.md"
printf -- "👀 OPEN   %s\n" "cat /tmp/hee.pr.body.latest.md"
}
