#!/usr/bin/env bash
set -euo pipefail

# HEE Guarded Git/GH Ops
# - Agents MUST NOT run raw mutating git/gh commands.
# - Mutations must route through this script.
# - Branch gating: refuse mutations on main/master.
# - Liveness gating: refuse mutations unless BOTH:
#     (a) --act is provided
#     (b) HEE_TOOL_MODE=ACT
#
# Exit codes:
#   42 = governance BLOCKER
#   2  = usage

BLOCKER_EXIT=42

say() { printf '%s\n' "$*" >&2; }
die() { say "$*"; exit 2; }
blocker() { say "BLOCKER: $*"; exit "$BLOCKER_EXIT"; }

current_branch() {
  git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "UNKNOWN"
}

is_protected_branch() {
  local b
  b="$(current_branch)"
  [[ "$b" == "main" || "$b" == "master" ]]
}

require_liveness() {
  local act_flag="${1:-}"
  local mode="${HEE_TOOL_MODE:-}"
  if [[ "$act_flag" != "1" ]]; then
    blocker "Mutation requested but --act missing. Refusing."
  fi
  if [[ "$mode" != "ACT" ]]; then
    blocker "Mutation requested but HEE_TOOL_MODE!=ACT (got: '${mode:-<unset>}'). Refusing."
  fi
}

require_liveness_for_mutation() {
  require_liveness "${1:-}"
  if is_protected_branch; then
    blocker "Mutation requested on protected branch '$(current_branch)'. Refusing."
  fi
}

usage() {
  cat >&2 <<'USAGE'
Usage:
  scripts/hee_git_ops.sh <op> [--act] --reason "..." [args...]

Ops (read-only):
  status
  diff [args...]
  log [args...]
  show [args...]
  branch-show

Ops (mutating; requires: --act AND HEE_TOOL_MODE=ACT; refuses on main/master):
  add <paths...>
  commit -m "msg" [--no-verify]
  push [--set-upstream origin <branch>]
  checkout <branch>            (treated as mutating if it changes HEAD)
  branch-create <name>
  tag-create <tagname> [-m "msg"] [<commit-ish>]
  pr-create --base <base> --title "..." --body "..." [--draft]

Notes:
- For mutations, the caller must set: HEE_TOOL_MODE=ACT
- This script is intentionally restrictive. Expand only via policy change + review.

Examples:
  scripts/hee_git_ops.sh status
  HEE_TOOL_MODE=ACT scripts/hee_git_ops.sh add --act --reason "stage runbook" docs/guides/GIT_GH_WORKFLOW.md
  HEE_TOOL_MODE=ACT scripts/hee_git_ops.sh commit --act --reason "commit governance" -m "Add HEE gitops admission control"
  HEE_TOOL_MODE=ACT scripts/hee_git_ops.sh push --act --reason "push branch"
  HEE_TOOL_MODE=ACT scripts/hee_git_ops.sh pr-create --act --reason "open PR" --base main --title "..." --body "..."
USAGE
}

# --- argument parsing (minimal but strict) ---
if [[ "${1:-}" == "" || "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

op="$1"; shift

act=0
reason=""

# We require --reason for all ops (including read-only) to force intentionality in agent logs.
# This is optional for humans, but "strongest form" makes it mandatory.
while [[ $# -gt 0 ]]; do
  case "$1" in
    --act) act=1; shift ;;
    --reason)
      shift
      [[ $# -gt 0 ]] || die "Missing value for --reason"
      reason="$1"
      shift
      ;;
    *)
      break
      ;;
  esac
done

if [[ -z "$reason" ]]; then
  blocker "Missing --reason. Refusing."
fi

# --- dispatch ---
case "$op" in
  status)
    git status
    ;;

  diff)
    git diff "$@"
    ;;

  log)
    git --no-pager log "$@"
    ;;

  show)
    git show "$@"
    ;;

  branch-show)
    current_branch
    ;;

  add)
    require_liveness_for_mutation "$act"
    [[ $# -gt 0 ]] || die "add requires <paths...>"
    git add "$@"
    ;;

  commit)
    require_liveness_for_mutation "$act"
    # allow passthrough of commit flags, but require -m
    if ! printf '%s\0' "$@" | tr '\0' '\n' | grep -qE '^-m$'; then
      die "commit requires -m \"message\""
    fi

# --- BEGIN: model disclosure precheck based on commit argv (-m) ---
extract_commit_message_from_args() {
  local msg=""
  local prev=""
  for a in "$@"; do
    if [ "$prev" = "-m" ] || [ "$prev" = "--message" ]; then
      if [ -n "$msg" ]; then
        msg="${msg}"$'\n'
      fi
      msg="${msg}${a}"
      prev=""
      continue
    fi
    prev="$a"
  done
  printf "%s" "$msg"
}

commit_msg="$(extract_commit_message_from_args "$@")"

if [ -n "${commit_msg:-}" ]; then
  tmp_msg="$(mktemp)"
  printf "%s\n" "$commit_msg" > "$tmp_msg"
  if [ -x "scripts/check_model_disclosure.sh" ]; then
    scripts/check_model_disclosure.sh "$tmp_msg" || { rm -f "$tmp_msg"; exit 1; }
  fi
  rm -f "$tmp_msg"
fi
# --- END: model disclosure precheck based on commit argv (-m) ---

git commit "$@"
    ;;

  push)
    require_liveness_for_mutation "$act"
    git push "$@"
    ;;

  checkout)
    # Same reasoning as branch-create: the thing actually worth blocking
    # is committing/pushing *while on* main, not leaving main to go work
    # on a branch -- gating checkout on the *current* (pre-checkout)
    # branch made it impossible to ever check out away from main, which
    # is the one time this op is actually needed. commit/push below still
    # fully enforce the real protection.
    require_liveness "$act"
    [[ $# -eq 1 ]] || die "checkout requires <branch>"
    git checkout "$1"
    ;;

  branch-create)
    # Deliberately not require_liveness_for_mutation: `git branch <name>`
    # from main doesn't touch main or move HEAD, and main is the only
    # place you'd ever actually call this from -- the protected-branch
    # gate made this op impossible to use for its own purpose. Found
    # 2026-08-18 on first real use (contracts/agent-instance-signature-v1).
    require_liveness "$act"
    [[ $# -eq 1 ]] || die "branch-create requires <name>"
    git branch "$1"
    ;;

  tag-create)
    require_liveness_for_mutation "$act"
    [[ $# -ge 1 ]] || die "tag-create requires <tagname> [-m \"msg\"] [<commit-ish>]"
    tag="$1"; shift
    # Support: -m "msg" optional, commit-ish optional.
    if [[ "${1:-}" == "-m" ]]; then
      shift
      [[ $# -gt 0 ]] || die "tag-create: missing message after -m"
      msg="$1"; shift
      if [[ $# -gt 0 ]]; then
        git tag -a "$tag" -m "$msg" "$1"
      else
        git tag -a "$tag" -m "$msg"
      fi
    else
      # lightweight tag is disallowed in strongest mode; require annotated tags only.
      blocker "Lightweight tags are disallowed. Use: tag-create <tag> -m \"msg\" [<commit-ish>]"
    fi
    ;;

  pr-create)
    require_liveness_for_mutation "$act"
    # Require explicit --base/--title/--body
    base=""
    title=""
    body=""
    draft=0
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --base) shift; base="${1:-}"; shift ;;
        --title) shift; title="${1:-}"; shift ;;
        --body) shift; body="${1:-}"; shift ;;
        --draft) draft=1; shift ;;
        *) die "Unknown pr-create arg: $1" ;;
      esac
    done
    [[ -n "$base" && -n "$title" && -n "$body" ]] || die "pr-create requires --base, --title, --body"
    if [[ "$draft" -eq 1 ]]; then
      gh pr create --base "$base" --title "$title" --body "$body" --draft
    else
      gh pr create --base "$base" --title "$title" --body "$body"
    fi
    ;;

  *)
    die "Unknown op: $op"
    ;;
esac
