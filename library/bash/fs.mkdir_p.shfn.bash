# shellboss library function
# source: ~/.local/bin/shellboss
# extracted: 2026-02-07T02:01:23
# NOTE: authoritative library; wrapper must not shadow logic.

sb_fs_mkdir_p() {
  d="$1"
  mkdir -p "$d"
  rc=$?
  if [ "$rc" -ne 0 ]; then
    sb_return_fail "$rc" "mkdir_failed"
    echo "SB_OP=fs.mkdir-p" >&2
    echo "SB_PATH=$d" >&2
    return "$rc"
  fi
  sb_return_ok
  echo "SB_OP=fs.mkdir-p"
  echo "SB_PATH=$d"
  return 0
}
