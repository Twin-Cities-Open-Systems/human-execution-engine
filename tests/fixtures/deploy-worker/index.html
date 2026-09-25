#!/bin/sh
# section: 8
# get-hee.sh -- install the hee toolchain from a public checkout.
#
#   curl -fsSL https://get.hee.tools | sh
#
# What it does, and nothing else:
#   1. git clone https://github.com/Twin-Cities-Open-Systems/human-execution-engine
#      at the `stable` ref into $HEE_REPO_DIR (default ~/git/human-execution-engine),
#      or fast-forward it if it is already there.
#   2. symlink ~/.local/bin/hee -> <checkout>/tooling/bin/hee
#   3. say whether ~/.local/bin is on PATH, and run `hee list` as proof.
#
# It never asks for sudo, never writes outside $HEE_REPO_DIR and
# ~/.local/bin, and is idempotent: run it again to update. `stable` is the
# ref other repos' CI pins (rule 16); it advances only after the consumer
# repos are measured green, which is exactly the property an installer
# wants.
#
# Why a checkout and not a tarball: every hee tool's --help is its man
# page and its tests, and `git pull` is the update mechanism for both.
# A copy would be a second thing to drift.
#
# ENVIRONMENT
#   HEE_REPO_DIR   where the checkout lives (default: $HOME/git/human-execution-engine)
#   HEE_REF        ref to check out (default: stable)
#   HEE_BIN_DIR    where the `hee` link goes (default: $HOME/.local/bin)
#
# EXIT STATUS
#   0  OK        installed or already current
#   2  CRITICAL  git missing, clone or checkout failed
#
# EXAMPLES
#   curl -fsSL https://get.hee.tools | sh
#   HEE_REPO_DIR=/opt/hee sh get-hee.sh
#   sh tooling/get-hee.sh --help   # ci
set -eu

case "${1:-}" in
  -h|--help|help)
    sed -n '3,/^set -eu/p' "$0" | sed '$d' | sed 's/^# \{0,1\}//'
    exit 0 ;;
esac

REPO_URL="https://github.com/Twin-Cities-Open-Systems/human-execution-engine"
HEE_REPO_DIR="${HEE_REPO_DIR:-$HOME/git/human-execution-engine}"
HEE_REF="${HEE_REF:-stable}"
HEE_BIN_DIR="${HEE_BIN_DIR:-$HOME/.local/bin}"

if ! command -v git >/dev/null 2>&1; then
  echo "CRITICAL: git is not installed; install it and run this again." >&2
  exit 2
fi

if [ -d "$HEE_REPO_DIR/.git" ]; then
  echo "OK: checkout exists at $HEE_REPO_DIR, updating to $HEE_REF"
  git -C "$HEE_REPO_DIR" fetch --quiet origin "$HEE_REF"
  git -C "$HEE_REPO_DIR" checkout --quiet "$HEE_REF"
  git -C "$HEE_REPO_DIR" merge --quiet --ff-only "origin/$HEE_REF" 2>/dev/null \
    || git -C "$HEE_REPO_DIR" reset --quiet --hard "origin/$HEE_REF"
else
  mkdir -p "$(dirname "$HEE_REPO_DIR")"
  echo "OK: cloning $REPO_URL ($HEE_REF) into $HEE_REPO_DIR"
  git clone --quiet --branch "$HEE_REF" "$REPO_URL" "$HEE_REPO_DIR"
fi

mkdir -p "$HEE_BIN_DIR"
ln -sfn "$HEE_REPO_DIR/tooling/bin/hee" "$HEE_BIN_DIR/hee"
echo "OK: $HEE_BIN_DIR/hee -> $HEE_REPO_DIR/tooling/bin/hee"

case ":$PATH:" in
  *":$HEE_BIN_DIR:"*) ;;
  *) echo "WARNING: $HEE_BIN_DIR is not on your PATH; add this to your shell rc:"
     echo "    export PATH=\"$HEE_BIN_DIR:\$PATH\"" ;;
esac

"$HEE_BIN_DIR/hee" list >/dev/null 2>&1 && echo "OK: hee $(git -C "$HEE_REPO_DIR" rev-parse --short HEAD) installed; try: hee list"
