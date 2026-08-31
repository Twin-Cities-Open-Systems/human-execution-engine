#!/usr/bin/env bash
# tests/status-parity.sh
#
# The bash and Python implementations of the HEE status vocabulary must
# agree exactly -- same levels, same exit codes, same rendered output in
# every style. A shell tool and a Python tool have to be indistinguishable
# in a log or a pipe, or the "one vocabulary" claim is false.
#
# Real trigger, 2026-08-31: the first version of the pair diverged
# immediately. Python accepted PASS/FAIL (the two most common legacy words
# in this tree -- 9 and 7 files) and bash did not, so identical input
# produced exit 0 from one and exit 3 from the other. A comment saying
# "keep these in sync" would not have caught it. This does.
#
# Usage: tests/status-parity.sh   (exit 0 = parity, 1 = divergence)

set -uo pipefail
cd "$(dirname "$0")/.." || exit 1

SHFN="library/bash/vis.status.shfn.bash"
PYLIB="library/py"

[ -r "$SHFN" ] || { echo "missing: $SHFN" >&2; exit 1; }
[ -d "$PYLIB/hee_status" ] || { echo "missing: $PYLIB/hee_status" >&2; exit 1; }

# Every alias either implementation claims to accept, plus junk and empty.
INPUTS=(OK WARNING CRITICAL UNKNOWN PASS FAIL SUCCESS FAILED ERROR WARN CRIT
        green yellow red GREEN YELLOW RED ok warning bogus "")
STYLES=(icon ascii plain)

fails=0

for input in "${INPUTS[@]}"; do
  py_code="$(PYTHONPATH="$PYLIB" python3 -c \
    "from hee_status import status; print(status('${input}').value)" 2>/dev/null)"
  ( . "$SHFN"; hee_status_code "$input" ); sh_code=$?

  if [ "$py_code" != "$sh_code" ]; then
    printf 'EXIT-CODE MISMATCH  input=%-10s python=%s bash=%s\n' \
      "${input:-<empty>}" "$py_code" "$sh_code" >&2
    fails=$((fails + 1))
  fi

  for style in "${STYLES[@]}"; do
    py_out="$(HEE_STATUS_STYLE="$style" PYTHONPATH="$PYLIB" python3 -c \
      "from hee_status import render; print(render('${input}','msg'))" 2>/dev/null)"
    sh_out="$( . "$SHFN"; HEE_STATUS_STYLE="$style" hee_status "$input" msg )"
    if [ "$py_out" != "$sh_out" ]; then
      printf 'RENDER MISMATCH     input=%-10s style=%-5s python=%q bash=%q\n' \
        "${input:-<empty>}" "$style" "$py_out" "$sh_out" >&2
      fails=$((fails + 1))
    fi
  done
done

if [ "$fails" -eq 0 ]; then
  echo "✅ OK status vocabulary parity: bash and python agree on ${#INPUTS[@]} inputs x ${#STYLES[@]} styles"
  exit 0
fi

echo "❌ CRITICAL status vocabulary parity: ${fails} divergence(s)" >&2
exit 1
