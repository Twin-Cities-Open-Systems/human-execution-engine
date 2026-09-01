# shellboss library function
# source: ~/.local/bin/shellboss
# extracted: 2026-02-07T02:01:23
# NOTE: authoritative library; wrapper must not shadow logic.

sb_fs_write_stdin() {
  out="$1"
  if [ -e "$out" ]; then
    sb_return_fail 73 "clobber_refused"
    echo "SB_OP=fs.write-stdin" >&2
    echo "SB_PATH=$out" >&2
    return 73
  fi
  mkdir -p "$(dirname "$out")"
  rc=$?
  if [ "$rc" -ne 0 ]; then
    sb_return_fail "$rc" "mkdir_failed"
    echo "SB_OP=fs.write-stdin" >&2
    echo "SB_PATH=$out" >&2
    return "$rc"
  fi
  cat > "$out"
  rc=$?
  if [ "$rc" -ne 0 ]; then
    sb_return_fail 2 "write_failed"
    echo "SB_OP=fs.write-stdin" >&2
    echo "SB_PATH=$out" >&2
    return 2
  fi
  sb_return_ok
  echo "SB_OP=fs.write-stdin"
  echo "SB_PATH=$out"
  sha256sum "$out"
  return 0
}
